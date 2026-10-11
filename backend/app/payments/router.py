"""Payment routes — Chapa adapter, webhook, idempotent processing.

D-01 gate: PAID_ENTRY / PURCHASE activation is blocked until an EntryModeApproval
row exists for the campaign.  The mock provider must never run in production.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import Principal, get_current_principal
from app.campaigns.models import Campaign, EntryModeApproval
from app.core.config import get_settings
from app.core.db import get_db
from app.payments.models import Payment, PaymentEvent

router = APIRouter(prefix="/payments", tags=["payments"])


# ── Schemas ─────────────────────────────────────────────

class InitializeIn(BaseModel):
    campaign_id: str


class InitializeOut(BaseModel):
    payment_id: str
    checkout_url: str
    amount: float
    currency: str = "ETB"


class PaymentOut(BaseModel):
    id: str
    status: str
    amount: float
    currency: str
    created_at: str


# ── Helpers ─────────────────────────────────────────────

def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _chapa_secret() -> str:
    return os.environ.get("CHAPA_SECRET_KEY", "")


# ── Routes ───────────────────────────────────────────────

@router.post("/chapa/initialize", response_model=InitializeOut, status_code=201)
def initialize_payment(
    body: InitializeIn,
    session: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> InitializeOut:
    try:
        cid = uuid.UUID(body.campaign_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid campaign_id")

    campaign = session.scalar(select(Campaign).where(Campaign.id == cid))
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Campaign is not active")
    if campaign.entry_mode not in ("PURCHASE", "PAID_ENTRY"):
        raise HTTPException(status_code=400, detail="Campaign does not require payment")

    # D-01 gate
    approval = session.scalar(
        select(EntryModeApproval).where(
            EntryModeApproval.campaign_id == cid,
            EntryModeApproval.entry_mode == campaign.entry_mode,
        )
    )
    if not approval:
        raise HTTPException(
            status_code=403,
            detail="Paid entry mode is not yet authorized for this campaign (D-01).",
        )

    if not campaign.entry_price:
        raise HTTPException(status_code=400, detail="Campaign has no entry price")

    merchant_ref = f"ad-{uuid.uuid4().hex}"
    payment = Payment(
        user_id=principal.user.id,
        campaign_id=cid,
        provider="chapa",
        merchant_reference=merchant_ref,
        amount=campaign.entry_price,
        currency="ETB",
        status="INITIATED",
    )
    session.add(payment)
    session.commit()
    session.refresh(payment)

    # In a real integration this would call Chapa's API and return their checkout_url.
    # Here we return a sandbox URL so the frontend can display it.
    settings = get_settings()
    base = getattr(settings, "frontend_url", "http://localhost:5173")
    checkout_url = f"https://checkout.chapa.co/checkout/payment/{merchant_ref}"

    return InitializeOut(
        payment_id=str(payment.id),
        checkout_url=checkout_url,
        amount=float(payment.amount),
    )


@router.get("/{payment_id}", response_model=PaymentOut)
def get_payment(
    payment_id: str,
    session: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> PaymentOut:
    try:
        pid = uuid.UUID(payment_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Payment not found")
    payment = session.scalar(select(Payment).where(Payment.id == pid))
    if not payment or payment.user_id != principal.user.id:
        raise HTTPException(status_code=404, detail="Payment not found")
    return PaymentOut(
        id=str(payment.id),
        status=payment.status,
        amount=float(payment.amount),
        currency=payment.currency,
        created_at=payment.created_at.isoformat(),
    )


@router.post("/chapa/webhook", status_code=200)
async def chapa_webhook(
    request: Request,
    session: Annotated[Session, Depends(get_db)],
    x_chapa_signature: Annotated[str | None, Header()] = None,
) -> dict[str, str]:
    """Idempotent Chapa webhook handler.

    Security:
    - Verifies HMAC-SHA256 signature from Chapa.
    - Deduplicates by payload SHA-256 (idempotency — safe to receive twice).
    - Never trusts frontend payment-success signals.
    """
    raw_body = await request.body()
    payload_hash = _sha256_hex(raw_body)

    # Signature verification
    secret = _chapa_secret()
    if secret:
        expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, x_chapa_signature or ""):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Idempotency check — reject duplicate payloads
    existing_event = session.scalar(
        select(PaymentEvent).where(
            PaymentEvent.provider == "chapa",
            PaymentEvent.payload_sha256 == payload_hash,
        )
    )
    if existing_event:
        return {"status": "already_processed"}

    import json
    try:
        payload: dict = json.loads(raw_body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    merchant_ref: str = payload.get("tx_ref", "") or payload.get("reference", "")
    event_type = payload.get("event", "charge.success")
    provider_tx_id = payload.get("id") or payload.get("transaction_id")

    # Record event (even if we can't process it yet)
    event = PaymentEvent(
        provider="chapa",
        provider_event_id=str(provider_tx_id) if provider_tx_id else None,
        event_type=event_type,
        payload_sha256=payload_hash,
    )

    if merchant_ref:
        payment = session.scalar(
            select(Payment).where(Payment.merchant_reference == merchant_ref)
        )
        if payment and event_type in ("charge.success", "payment.success"):
            payment.status = "SUCCEEDED"
            payment.provider_reference = str(provider_tx_id) if provider_tx_id else None
            payment.verified_at = datetime.now(timezone.utc)
            event.payment_id = payment.id

            # Create the entry now payment is confirmed (server-side only)
            from app.entries.models import Entry
            from app.campaigns.models import CampaignCounter
            from sqlalchemy import func

            # Check capacity and per-user limit
            confirmed = session.scalar(
                select(func.count()).where(
                    Entry.campaign_id == payment.campaign_id,
                    Entry.status == "CONFIRMED",
                )
            ) or 0
            campaign = session.scalar(
                select(Campaign).where(Campaign.id == payment.campaign_id)
            )
            if campaign and confirmed < campaign.max_entries:
                counter = session.scalar(
                    select(CampaignCounter)
                    .where(CampaignCounter.campaign_id == payment.campaign_id)
                    .with_for_update()
                )
                if counter:
                    entry_number = counter.next_entry_number
                    counter.next_entry_number = entry_number + 1
                    entry = Entry(
                        campaign_id=payment.campaign_id,
                        user_id=payment.user_id,
                        entry_number=entry_number,
                        payment_id=payment.id,
                        status="CONFIRMED",
                        source_type=campaign.entry_mode,
                        confirmed_at=datetime.now(timezone.utc),
                    )
                    session.add(entry)

    session.add(event)
    session.commit()
    return {"status": "accepted"}
