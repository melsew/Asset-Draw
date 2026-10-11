"""Entry routes — thin HTTP adapter over the Eligibility & Entry Engine.

The engine (entries/eligibility.py) answers the six eligibility questions
and creates entries with the correct trigger-compatible two-step flow.
This router only handles HTTP concerns: auth, UUID parsing, response shape,
and translating EligibilityCode → HTTP status.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.auth.dependencies import Principal, get_current_principal
from app.campaigns.models import Campaign
from app.core.db import get_db
from app.entries.eligibility import (
    EligibilityCode,
    check_eligibility,
    create_entry,
)
from app.entries.models import Entry

router = APIRouter(tags=["entries"])


# ── Output schema ─────────────────────────────────────────────────────────────

class EntryOut(BaseModel):
    id: str
    entry_number: str
    campaign_id: str
    campaign_title: str
    campaign_prize: str
    status: str
    created_at: str
    draw_at: str | None = None
    campaign_status: str

    model_config = {"from_attributes": True}


class ParticipateIn(BaseModel):
    """Optional request body for modes that require extra context."""
    payment_id: str | None = None     # required for PURCHASE / PAID_ENTRY
    referral_code: str | None = None  # required for REFERRAL


# ── Eligibility code → HTTP status mapping ────────────────────────────────────

_HTTP_STATUS: dict[EligibilityCode, int] = {
    EligibilityCode.USER_NOT_ACTIVE:        status.HTTP_403_FORBIDDEN,
    EligibilityCode.PHONE_NOT_VERIFIED:     status.HTTP_403_FORBIDDEN,
    EligibilityCode.CAMPAIGN_NOT_FOUND:     status.HTTP_404_NOT_FOUND,
    EligibilityCode.CAMPAIGN_NOT_ACTIVE:    status.HTTP_400_BAD_REQUEST,
    EligibilityCode.PARTICIPATION_CLOSED:   status.HTTP_400_BAD_REQUEST,
    EligibilityCode.ALREADY_ENTERED:        status.HTTP_409_CONFLICT,
    EligibilityCode.CAMPAIGN_FULL:          status.HTTP_409_CONFLICT,
    EligibilityCode.D01_GATE_PAID_ENTRY:    status.HTTP_403_FORBIDDEN,
    EligibilityCode.PAYMENT_REQUIRED:       status.HTTP_402_PAYMENT_REQUIRED,
    EligibilityCode.PAYMENT_NOT_CONFIRMED:  status.HTTP_402_PAYMENT_REQUIRED,
    EligibilityCode.REFERRAL_NOT_VERIFIED:  status.HTTP_403_FORBIDDEN,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _prize_name(session: Session, campaign_id: uuid.UUID) -> str:
    from app.campaigns.models import CampaignPrize
    from app.assets.models import Asset
    cp = session.scalar(
        select(CampaignPrize).where(
            CampaignPrize.campaign_id == campaign_id,
            CampaignPrize.prize_index == 0,
        )
    )
    if cp:
        asset = session.scalar(select(Asset).where(Asset.id == cp.asset_id))
        if asset:
            return asset.name
    return "Prize"


def _entry_to_out(entry: Entry, session: Session) -> EntryOut:
    campaign = session.scalar(select(Campaign).where(Campaign.id == entry.campaign_id))
    return EntryOut(
        id=str(entry.id),
        entry_number=str(entry.entry_number) if entry.entry_number is not None else "—",
        campaign_id=str(entry.campaign_id),
        campaign_title=campaign.title if campaign else "Unknown",
        campaign_prize=_prize_name(session, entry.campaign_id),
        status=entry.status,
        created_at=entry.created_at.isoformat(),
        draw_at=campaign.draw_at.isoformat() if campaign and campaign.draw_at else None,
        campaign_status=campaign.status if campaign else "UNKNOWN",
    )


def _db_error_to_http(exc: DBAPIError) -> HTTPException:
    """Last-resort translation when the DB trigger fires after our Python checks."""
    sqlstate = getattr(exc.orig, "sqlstate", None)
    msg = str(getattr(exc.orig, "pgerror", exc))
    if sqlstate == "23514":
        if "capacity" in msg:
            return HTTPException(status_code=409, detail="Campaign is full")
        if "participant entry limit" in msg or "per_user" in msg:
            return HTTPException(status_code=409, detail="Entry limit reached")
        if "start as pending" in msg or "pending without" in msg:
            return HTTPException(status_code=500, detail="Entry creation protocol error")
        if "active campaigns" in msg or "only be reserved" in msg:
            return HTTPException(status_code=400, detail="Campaign is not accepting entries")
    if sqlstate == "55000":
        return HTTPException(status_code=409, detail="Entries are locked — pool is closed")
    return HTTPException(status_code=400, detail="Entry could not be created")


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post(
    "/campaigns/{campaign_id}/participate",
    response_model=EntryOut,
    status_code=status.HTTP_201_CREATED,
)
def participate(
    campaign_id: str,
    session: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    body: ParticipateIn | None = None,
) -> EntryOut:
    """Participate in a campaign.

    Runs the full six-check eligibility engine before creating the entry.
    The entry is created in two DB steps (PENDING then CONFIRMED) to satisfy
    the enforce_entry_capacity trigger.

    Returns 201 with the confirmed entry including the assigned entry number.
    """
    try:
        cid = uuid.UUID(campaign_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Campaign not found")

    payment_id: uuid.UUID | None = None
    referral_code: str | None = None

    if body:
        if body.payment_id:
            try:
                payment_id = uuid.UUID(body.payment_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid payment_id")
        referral_code = body.referral_code

    # ── Run all six eligibility checks ────────────────────────────────────────
    result = check_eligibility(
        session,
        principal.user,
        cid,
        payment_id=payment_id,
        referral_code=referral_code,
    )

    if not result.eligible:
        http_status = _HTTP_STATUS.get(result.code, 400)
        raise HTTPException(status_code=http_status, detail=result.message)

    # ── Retrieve campaign.entry_mode for source_type ──────────────────────────
    campaign = session.scalar(select(Campaign).where(Campaign.id == cid))
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # ── Create the entry (two-step PENDING → CONFIRMED) ───────────────────────
    try:
        entry = create_entry(
            session,
            user_id=principal.user.id,
            campaign_id=cid,
            entry_mode=campaign.entry_mode,
            payment_id=payment_id,
        )
        session.commit()
    except DBAPIError as exc:
        session.rollback()
        raise _db_error_to_http(exc) from exc

    session.refresh(entry)
    return _entry_to_out(entry, session)


@router.get(
    "/campaigns/{campaign_id}/eligibility",
    summary="Check participation eligibility without creating an entry",
)
def check_campaign_eligibility(
    campaign_id: str,
    session: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> dict[str, object]:
    """Dry-run eligibility check for the campaign detail page.

    Returns a structured result so the UI can show the correct CTA:
      - eligible=true  → show 'Get my entry' button
      - eligible=false → show the reason and disable the button
    """
    try:
        cid = uuid.UUID(campaign_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Campaign not found")

    result = check_eligibility(session, principal.user, cid)
    return {
        "eligible": result.eligible,
        "code": result.code.value,
        "message": result.message,
    }


@router.get("/users/me/entries", response_model=list[EntryOut])
def my_entries(
    session: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[EntryOut]:
    entries = session.scalars(
        select(Entry)
        .where(Entry.user_id == principal.user.id)
        .order_by(Entry.created_at.desc())
    ).all()
    return [_entry_to_out(e, session) for e in entries]
