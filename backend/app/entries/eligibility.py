"""Eligibility & Entry Engine — the authoritative gate for campaign participation.

Answers the six mandatory questions in order:

  1. Is the user eligible?          (account active; phone verified for paid modes)
  2. Is the campaign active?        (status = ACTIVE)
  3. Is participation still open?   (end_at has not passed)
  4. Has the user already entered?  (per-user limit not reached)
  5. Is campaign capacity available?(max_entries not reached)
  6. Has the qualifying action been verified? (entry_mode gate + D-01 lock)

This module is a pure service layer: no HTTP, no FastAPI dependencies.
The router calls check_eligibility(), inspects the result, and either
calls create_entry() or raises an appropriate HTTP error.

TRIGGER CONTRACT:
  The PostgreSQL trigger enforce_entry_capacity() enforces questions 4 and 5
  atomically at the database level as a last line of defence.  This module
  performs the same checks in Python first so that:
    - The caller receives a structured EligibilityResult (not a raw DBAPIError)
    - The reason for refusal is auditable and localisation-friendly
  If the trigger fires *after* our checks (race condition), the DBAPIError
  is caught in entries/router.py and translated to a 409.

  The trigger also enforces:
    - entries must start as PENDING (no entry_number on INSERT)
    - entry_number is assigned atomically on PENDING → CONFIRMED
  create_entry() respects this by always inserting PENDING then updating CONFIRMED.
"""
from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.campaigns.models import (
    Campaign,
    CampaignCounter,
    EntryModeApproval,
)
from app.entries.models import Entry
from app.users.models import User


# ── Result type ───────────────────────────────────────────────────────────────

class EligibilityCode(str, enum.Enum):
    """Machine-readable reason code returned to the router."""

    OK                      = "OK"
    USER_NOT_ACTIVE         = "USER_NOT_ACTIVE"
    PHONE_NOT_VERIFIED      = "PHONE_NOT_VERIFIED"
    CAMPAIGN_NOT_FOUND      = "CAMPAIGN_NOT_FOUND"
    CAMPAIGN_NOT_ACTIVE     = "CAMPAIGN_NOT_ACTIVE"
    PARTICIPATION_CLOSED    = "PARTICIPATION_CLOSED"
    ALREADY_ENTERED         = "ALREADY_ENTERED"
    CAMPAIGN_FULL           = "CAMPAIGN_FULL"
    D01_GATE_PAID_ENTRY     = "D01_GATE_PAID_ENTRY"
    PAYMENT_REQUIRED        = "PAYMENT_REQUIRED"
    PAYMENT_NOT_CONFIRMED   = "PAYMENT_NOT_CONFIRMED"
    REFERRAL_NOT_VERIFIED   = "REFERRAL_NOT_VERIFIED"


# Human-readable messages keyed by code (English; Amharic served by i18n on the frontend)
_MESSAGES: dict[EligibilityCode, str] = {
    EligibilityCode.OK:                      "Eligible",
    EligibilityCode.USER_NOT_ACTIVE:         "Your account is not active",
    EligibilityCode.PHONE_NOT_VERIFIED:      "Phone number must be verified to participate",
    EligibilityCode.CAMPAIGN_NOT_FOUND:      "Campaign not found",
    EligibilityCode.CAMPAIGN_NOT_ACTIVE:     "Campaign is not currently accepting entries",
    EligibilityCode.PARTICIPATION_CLOSED:    "Participation period has ended",
    EligibilityCode.ALREADY_ENTERED:         "You have already entered this campaign",
    EligibilityCode.CAMPAIGN_FULL:           "Campaign has reached maximum capacity",
    EligibilityCode.D01_GATE_PAID_ENTRY:     "Paid entry is not yet authorised (decision D-01 pending)",
    EligibilityCode.PAYMENT_REQUIRED:        "A confirmed payment is required to enter this campaign",
    EligibilityCode.PAYMENT_NOT_CONFIRMED:   "Payment has not been confirmed by the provider",
    EligibilityCode.REFERRAL_NOT_VERIFIED:   "A verified referral is required to enter this campaign",
}


@dataclass(frozen=True)
class EligibilityResult:
    eligible: bool
    code: EligibilityCode
    message: str
    # Extra context for the router/audit layer; never sent to the user verbatim
    detail: dict[str, object] | None = None

    @classmethod
    def allow(cls) -> "EligibilityResult":
        return cls(eligible=True, code=EligibilityCode.OK, message=_MESSAGES[EligibilityCode.OK])

    @classmethod
    def deny(
        cls,
        code: EligibilityCode,
        detail: dict[str, object] | None = None,
    ) -> "EligibilityResult":
        return cls(
            eligible=False,
            code=code,
            message=_MESSAGES[code],
            detail=detail,
        )


# ── Public API ────────────────────────────────────────────────────────────────

def check_eligibility(
    session: Session,
    user: User,
    campaign_id: uuid.UUID,
    *,
    payment_id: uuid.UUID | None = None,
    referral_code: str | None = None,
) -> EligibilityResult:
    """Run all six eligibility checks in order.

    Returns EligibilityResult.eligible=True only when every check passes.
    The first failing check short-circuits; later checks are not evaluated.

    Args:
        session:       Active SQLAlchemy session (not committed by this function).
        user:          The authenticated User making the participation request.
        campaign_id:   Campaign UUID to enter.
        payment_id:    UUID of a confirmed Payment (required for PURCHASE/PAID_ENTRY).
        referral_code: Verified referral reference (required for REFERRAL mode).
    """
    # ── Q1: Is the user eligible? ─────────────────────────────────────────────
    if user.status != "ACTIVE":
        return EligibilityResult.deny(EligibilityCode.USER_NOT_ACTIVE, {"user_id": str(user.id)})

    # ── Load campaign ─────────────────────────────────────────────────────────
    campaign = session.scalar(select(Campaign).where(Campaign.id == campaign_id))
    if campaign is None:
        return EligibilityResult.deny(EligibilityCode.CAMPAIGN_NOT_FOUND, {"campaign_id": str(campaign_id)})

    # ── Q2: Is the campaign active? ───────────────────────────────────────────
    if campaign.status != "ACTIVE":
        return EligibilityResult.deny(
            EligibilityCode.CAMPAIGN_NOT_ACTIVE,
            {"campaign_id": str(campaign_id), "status": campaign.status},
        )

    # ── Q3: Is participation still open? ─────────────────────────────────────
    now = datetime.now(timezone.utc)
    if campaign.end_at < now:
        return EligibilityResult.deny(
            EligibilityCode.PARTICIPATION_CLOSED,
            {"campaign_id": str(campaign_id), "end_at": campaign.end_at.isoformat()},
        )

    # ── Q4: Has the user already participated? ────────────────────────────────
    existing = session.scalar(
        select(func.count()).where(
            Entry.campaign_id == campaign_id,
            Entry.user_id == user.id,
            Entry.status.in_(("PENDING", "CONFIRMED")),
        )
    ) or 0
    if existing >= campaign.per_user_limit:
        return EligibilityResult.deny(
            EligibilityCode.ALREADY_ENTERED,
            {
                "campaign_id": str(campaign_id),
                "user_id": str(user.id),
                "existing": existing,
                "per_user_limit": campaign.per_user_limit,
            },
        )

    # ── Q5: Is campaign capacity available? ───────────────────────────────────
    # Count PENDING + CONFIRMED to reserve as much headroom as possible.
    # The database trigger does the final atomic check under lock.
    active_entries = session.scalar(
        select(func.count()).where(
            Entry.campaign_id == campaign_id,
            Entry.status.in_(("PENDING", "CONFIRMED")),
        )
    ) or 0
    if active_entries >= campaign.max_entries:
        return EligibilityResult.deny(
            EligibilityCode.CAMPAIGN_FULL,
            {
                "campaign_id": str(campaign_id),
                "active_entries": active_entries,
                "max_entries": campaign.max_entries,
            },
        )

    # ── Q6: Has the qualifying action been verified? ──────────────────────────
    result = _check_qualifying_action(
        session, campaign, user.id, payment_id=payment_id, referral_code=referral_code
    )
    if not result.eligible:
        return result

    return EligibilityResult.allow()


def _check_qualifying_action(
    session: Session,
    campaign: Campaign,
    user_id: uuid.UUID,
    *,
    payment_id: uuid.UUID | None,
    referral_code: str | None,
) -> EligibilityResult:
    """Gate on entry_mode.  Each mode has its own verification path.

    FREE / PROMOTIONAL:
        No external action required.  These are the only modes permitted
        until D-01 is resolved.

    PURCHASE / PAID_ENTRY:
        A confirmed, server-side-verified Payment row is required.
        D-01 must be resolved and an entry_mode_approvals row must exist.

    REFERRAL:
        A verified referral reference is required (future; not yet implemented).
    """
    mode = campaign.entry_mode

    if mode in ("FREE", "PROMOTIONAL"):
        # No qualifying action beyond account existence.
        return EligibilityResult.allow()

    if mode in ("PURCHASE", "PAID_ENTRY"):
        # D-01 gate: block paid modes until a legal approval row exists
        approval = session.scalar(
            select(EntryModeApproval).where(
                EntryModeApproval.campaign_id == campaign.id,
                EntryModeApproval.entry_mode == mode,
            )
        )
        if approval is None:
            return EligibilityResult.deny(
                EligibilityCode.D01_GATE_PAID_ENTRY,
                {"campaign_id": str(campaign.id), "entry_mode": mode},
            )

        # Payment must be supplied by the caller
        if payment_id is None:
            return EligibilityResult.deny(
                EligibilityCode.PAYMENT_REQUIRED,
                {"campaign_id": str(campaign.id), "entry_mode": mode},
            )

        # Verify the payment server-side — NEVER trust a client-supplied status
        from app.payments.models import Payment as PaymentModel  # local import to avoid circular
        payment = session.scalar(
            select(PaymentModel).where(
                PaymentModel.id == payment_id,
                PaymentModel.campaign_id == campaign.id,
                PaymentModel.user_id == user_id,
            )
        )
        if payment is None or payment.status != "SUCCEEDED":
            return EligibilityResult.deny(
                EligibilityCode.PAYMENT_NOT_CONFIRMED,
                {
                    "campaign_id": str(campaign.id),
                    "payment_id": str(payment_id),
                    "payment_status": payment.status if payment else None,
                },
            )
        return EligibilityResult.allow()

    if mode == "REFERRAL":
        # TODO: implement referral verification service (future phase)
        if not referral_code:
            return EligibilityResult.deny(
                EligibilityCode.REFERRAL_NOT_VERIFIED,
                {"campaign_id": str(campaign.id)},
            )
        # Placeholder: referral code verified by source_reference lookup
        existing_referral = session.scalar(
            select(Entry).where(
                Entry.campaign_id == campaign.id,
                Entry.source_type == "REFERRAL",
                Entry.source_reference == referral_code,
                Entry.status == "CONFIRMED",
            )
        )
        if existing_referral is None:
            return EligibilityResult.deny(
                EligibilityCode.REFERRAL_NOT_VERIFIED,
                {"campaign_id": str(campaign.id), "referral_code": referral_code},
            )
        return EligibilityResult.allow()

    # Unrecognised mode — treat as ineligible
    return EligibilityResult.deny(
        EligibilityCode.CAMPAIGN_NOT_ACTIVE,
        {"campaign_id": str(campaign.id), "unknown_mode": mode},
    )


# ── Entry creation ────────────────────────────────────────────────────────────

def create_entry(
    session: Session,
    user_id: uuid.UUID,
    campaign_id: uuid.UUID,
    entry_mode: str,
    *,
    payment_id: uuid.UUID | None = None,
    source_reference: str | None = None,
) -> Entry:
    """Create an entry in two steps required by the enforce_entry_capacity trigger.

    Step 1: INSERT with status=PENDING, entry_number=NULL
    Step 2: UPDATE status=CONFIRMED — the trigger atomically assigns entry_number

    Raises:
        sqlalchemy.exc.DBAPIError — if the trigger rejects the insert or update.
        The caller (router) translates these to HTTP errors.

    Note: does NOT commit. The caller owns the transaction.
    """
    # Step 1 — PENDING insert (trigger validates capacity + per-user limit)
    entry = Entry(
        campaign_id=campaign_id,
        user_id=user_id,
        status="PENDING",        # trigger requires PENDING on INSERT
        # entry_number omitted — trigger will set it
        source_type=entry_mode,
        source_reference=source_reference,
        payment_id=payment_id,
    )
    session.add(entry)
    session.flush()  # fire INSERT trigger; raises DBAPIError on any violation

    # Step 2 — CONFIRMED update (trigger assigns entry_number atomically)
    entry.status = "CONFIRMED"
    session.flush()  # fire UPDATE trigger

    return entry
