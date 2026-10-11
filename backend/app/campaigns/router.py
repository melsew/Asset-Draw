"""Campaign routes — read-only consumer view + vendor/admin write paths.

TRIGGER AWARENESS:
  The PostgreSQL trigger enforce_campaign_status() fires on every status UPDATE.
  It automatically:
    - Validates transitions (raises 23514 if invalid)
    - Inserts campaign_status_history (append-only; never insert it manually)
    - Inserts campaign_counters when ACTIVE (never insert it manually)
  The trigger reads app.actor_user_id and app.reason session settings.

  To record who made a transition, set those session vars before the UPDATE:
    SET LOCAL app.actor_user_id = '<uuid>';
    SET LOCAL app.reason = '<optional reason>';

  Inserting a campaign with status='DRAFT' is allowed; any other initial status
  raises SQLSTATE 23514.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.assets.models import Asset
from app.auth.dependencies import Principal, get_current_principal, require_roles
from app.campaigns.models import Campaign, CampaignPrize, EntryModeApproval
from app.core.db import get_db
from app.core.demo_store import demo_get_campaign, demo_list_campaigns, is_demo_mode
from app.vendors.models import Vendor, VendorUser

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


# ── Output schema ─────────────────────────────────────────────────────────────

class CampaignOut(BaseModel):
    id: str
    title: str
    vendor: str
    prize: str
    description: str
    entry_mode: str
    entries: int
    max_entries: int
    status: str
    ends_at: str
    draw_at: str | None = None
    prize_image_url: str | None = None
    entry_price: float | None = None
    prize_value: float | None = None

    model_config = {"from_attributes": True}


# ── Input schemas ─────────────────────────────────────────────────────────────

class CampaignCreateIn(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=10, max_length=4000)
    entry_mode: str = Field("FREE")
    entry_price: float | None = None
    max_entries: int = Field(..., gt=0, le=1_000_000)
    per_user_limit: int = Field(1, gt=0, le=100)
    start_at: str
    end_at: str
    draw_at: str
    asset_id: str


# ── Internal helpers ──────────────────────────────────────────────────────────

def _confirmed_entry_count(session: Session, campaign_id: uuid.UUID) -> int:
    from app.entries.models import Entry
    return session.scalar(
        select(func.count()).where(
            Entry.campaign_id == campaign_id,
            Entry.status == "CONFIRMED",
        )
    ) or 0


def _primary_prize_name(session: Session, campaign_id: uuid.UUID) -> tuple[str, float | None]:
    """Return (asset_name, declared_value) for prize_index=0, or defaults."""
    cp = session.scalar(
        select(CampaignPrize).where(
            CampaignPrize.campaign_id == campaign_id,
            CampaignPrize.prize_index == 0,
        )
    )
    if cp:
        asset = session.scalar(select(Asset).where(Asset.id == cp.asset_id))
        if asset:
            return asset.name, float(asset.declared_value)
    return "Prize", None


def _campaign_to_out(c: Campaign, session: Session) -> CampaignOut:
    vendor = session.scalar(select(Vendor).where(Vendor.id == c.vendor_id))
    prize_name, prize_value = _primary_prize_name(session, c.id)
    return CampaignOut(
        id=str(c.id),
        title=c.title,
        vendor=vendor.display_name if vendor else "Unknown",
        prize=prize_name,
        description=c.description,
        entry_mode=c.entry_mode,
        entries=_confirmed_entry_count(session, c.id),
        max_entries=c.max_entries,
        status=c.status,
        ends_at=c.end_at.isoformat(),
        draw_at=c.draw_at.isoformat() if c.draw_at else None,
        entry_price=float(c.entry_price) if c.entry_price else None,
        prize_value=prize_value,
    )


def _demo_campaign_to_out(c: dict[str, object]) -> CampaignOut:
    return CampaignOut(
        id=str(c["id"]),
        title=str(c["title"]),
        vendor=str(c["vendor"]),
        prize=str(c["prize"]),
        description=str(c["description"]),
        entry_mode=str(c["entry_mode"]),
        entries=int(c["entries"]),
        max_entries=int(c["max_entries"]),
        status=str(c["status"]),
        ends_at=str(c["ends_at"]),
        draw_at=str(c["draw_at"]) if c.get("draw_at") else None,
        entry_price=None if c.get("entry_price") is None else float(c["entry_price"]),
        prize_value=None if c.get("prize_value") is None else float(c["prize_value"]),
    )


def _set_actor(session: Session, actor_id: uuid.UUID) -> None:
    """Tell the enforce_campaign_status trigger who is making this transition."""
    session.execute(text("SET LOCAL app.actor_user_id = :uid"), {"uid": str(actor_id)})


def _transition_status(
    session: Session,
    campaign: Campaign,
    new_status: str,
    actor_id: uuid.UUID,
    reason: str | None = None,
) -> None:
    """Safely update campaign status; let the DB trigger validate and record history."""
    _set_actor(session, actor_id)
    if reason:
        session.execute(text("SET LOCAL app.reason = :r"), {"r": reason})
    try:
        campaign.status = new_status
        session.flush()
    except DBAPIError as exc:
        sqlstate = getattr(exc.orig, "sqlstate", None)
        if sqlstate == "23514":
            raise HTTPException(
                status_code=400,
                detail=f"Transition to '{new_status}' is not permitted from '{campaign.status}'",
            ) from exc
        raise


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[CampaignOut])
def list_campaigns(
    session: Annotated[Session, Depends(get_db)],
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = Query(None),
) -> list[CampaignOut]:
    if is_demo_mode():
        return [_demo_campaign_to_out(c) for c in demo_list_campaigns(status_filter, search)]

    q = select(Campaign)
    if status_filter:
        q = q.where(Campaign.status == status_filter)
    else:
        q = q.where(
            Campaign.status.in_(
                ("ACTIVE", "SCHEDULED", "ENTRY_CLOSED", "POOL_LOCKED",
                 "DRAWING", "DRAW_COMPLETED", "WINNER_VERIFIED",
                 "PRIZE_DELIVERED", "COMPLETED")
            )
        )
    if search:
        term = f"%{search}%"
        q = q.where(Campaign.title.ilike(term) | Campaign.description.ilike(term))
    q = q.order_by(Campaign.start_at.desc())
    campaigns = session.scalars(q).all()
    return [_campaign_to_out(c, session) for c in campaigns]


@router.get("/{campaign_id}", response_model=CampaignOut)
def get_campaign(
    campaign_id: str,
    session: Annotated[Session, Depends(get_db)],
) -> CampaignOut:
    if is_demo_mode():
        c = demo_get_campaign(campaign_id)
        if c is None:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return _demo_campaign_to_out(c)

    try:
        cid = uuid.UUID(campaign_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Campaign not found")
    c = session.scalar(select(Campaign).where(Campaign.id == cid))
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return _campaign_to_out(c, session)


@router.post("", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
def create_campaign(
    body: CampaignCreateIn,
    session: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(require_roles("VENDOR", "ADMIN", "SUPER_ADMIN"))],
) -> CampaignOut:
    """Create a campaign in DRAFT status.

    The DB trigger enforces that campaigns are always inserted as DRAFT.
    No history row or counter row is created here — the trigger handles both
    at the correct transition points.
    """
    try:
        asset_id = uuid.UUID(body.asset_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid asset_id")

    asset = session.scalar(select(Asset).where(Asset.id == asset_id))
    if not asset:
        raise HTTPException(status_code=400, detail="Asset not found")

    # Resolve vendor
    vu = session.scalar(select(VendorUser).where(VendorUser.user_id == principal.user.id))
    is_admin = "ADMIN" in principal.roles or "SUPER_ADMIN" in principal.roles
    if not vu and not is_admin:
        raise HTTPException(status_code=403, detail="No vendor account found")
    vendor_id = vu.vendor_id if vu else asset.vendor_id

    # Validate entry_mode / entry_price consistency
    if body.entry_mode not in ("FREE", "PROMOTIONAL", "PURCHASE", "PAID_ENTRY", "REFERRAL"):
        raise HTTPException(status_code=400, detail=f"Invalid entry_mode: {body.entry_mode}")
    if body.entry_mode in ("PURCHASE", "PAID_ENTRY") and not body.entry_price:
        raise HTTPException(status_code=400, detail="entry_price required for PURCHASE/PAID_ENTRY")
    if body.entry_mode not in ("PURCHASE", "PAID_ENTRY") and body.entry_price is not None:
        raise HTTPException(status_code=400, detail="entry_price must be null for non-paid modes")

    try:
        start_at = datetime.fromisoformat(body.start_at).replace(tzinfo=timezone.utc) \
            if not datetime.fromisoformat(body.start_at).tzinfo \
            else datetime.fromisoformat(body.start_at)
        end_at = datetime.fromisoformat(body.end_at).replace(tzinfo=timezone.utc) \
            if not datetime.fromisoformat(body.end_at).tzinfo \
            else datetime.fromisoformat(body.end_at)
        draw_at = datetime.fromisoformat(body.draw_at).replace(tzinfo=timezone.utc) \
            if not datetime.fromisoformat(body.draw_at).tzinfo \
            else datetime.fromisoformat(body.draw_at)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {exc}") from exc

    if end_at <= start_at:
        raise HTTPException(status_code=400, detail="end_at must be after start_at")

    # Create campaign — the trigger will validate status='DRAFT' on INSERT
    c = Campaign(
        vendor_id=vendor_id,
        title=body.title,
        description=body.description,
        entry_mode=body.entry_mode,
        entry_price=Decimal(str(body.entry_price)) if body.entry_price else None,
        max_entries=body.max_entries,
        per_user_limit=body.per_user_limit,
        start_at=start_at,
        end_at=end_at,
        draw_at=draw_at,
        # status is omitted — server_default='DRAFT' is used; trigger validates it
        created_by=principal.user.id,
    )
    session.add(c)
    session.flush()  # get c.id

    # Attach the prize asset
    cp = CampaignPrize(campaign_id=c.id, prize_index=0, asset_id=asset_id)
    session.add(cp)

    # NOTE: CampaignStatusHistory is NOT inserted here.
    # The enforce_campaign_status trigger records history on every status UPDATE.
    # DRAFT is the initial INSERT value, not an UPDATE, so no history row is created
    # at this point — which is correct: there is no "from" status.

    session.commit()
    session.refresh(c)
    return _campaign_to_out(c, session)


@router.post("/{campaign_id}/submit", response_model=CampaignOut)
def submit_campaign(
    campaign_id: str,
    session: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(require_roles("VENDOR", "ADMIN", "SUPER_ADMIN"))],
) -> CampaignOut:
    """Vendor submits a DRAFT campaign for review.

    The DB trigger records the DRAFT→SUBMITTED transition in campaign_status_history.
    """
    try:
        cid = uuid.UUID(campaign_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Campaign not found")

    c = session.scalar(select(Campaign).where(Campaign.id == cid))
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")

    _transition_status(session, c, "SUBMITTED", principal.user.id)
    session.commit()
    session.refresh(c)
    return _campaign_to_out(c, session)
