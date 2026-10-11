"""Admin routes — campaign approval, vendor management.

TRIGGER AWARENESS:
  enforce_campaign_status() records campaign_status_history automatically
  on every status UPDATE. Never insert history rows manually here.

  The full transition path for activation:
    DRAFT → SUBMITTED → UNDER_REVIEW → APPROVED → ASSET_VERIFIED → SCHEDULED → ACTIVE

  Admins drive SUBMITTED → UNDER_REVIEW → APPROVED, and optionally
  APPROVED → ASSET_VERIFIED → SCHEDULED → ACTIVE in sequence.
  Each step must be taken one at a time; the trigger enforces adjacency.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.assets.models import Asset
from app.auth.dependencies import Principal, require_roles
from app.campaigns.models import Campaign, CampaignPrize
from app.core.db import get_db
from app.draws.models import Draw
from app.vendors.models import Vendor

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class CampaignOut(BaseModel):
    id: str
    title: str
    vendor: str
    prize: str
    status: str
    entry_mode: str
    max_entries: int
    draw_at: str | None = None


class VendorOut(BaseModel):
    id: str
    legal_name: str
    display_name: str
    status: str
    contact_email: str | None = None


class DrawOut(BaseModel):
    id: str
    campaign_id: str
    campaign_title: str
    status: str
    pool_locked_at: str | None = None
    executed_at: str | None = None
    planned_entropy_source: str | None = None
    planned_entropy_round: int | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _prize_name(session: Session, campaign: Campaign) -> str:
    cp = session.scalar(
        select(CampaignPrize).where(
            CampaignPrize.campaign_id == campaign.id,
            CampaignPrize.prize_index == 0,
        )
    )
    if cp:
        asset = session.scalar(select(Asset).where(Asset.id == cp.asset_id))
        if asset:
            return asset.name
    return "Prize"


def _campaign_to_out(c: Campaign, session: Session) -> CampaignOut:
    vendor = session.scalar(select(Vendor).where(Vendor.id == c.vendor_id))
    return CampaignOut(
        id=str(c.id),
        title=c.title,
        vendor=vendor.display_name if vendor else "Unknown",
        prize=_prize_name(session, c),
        status=c.status,
        entry_mode=c.entry_mode,
        max_entries=c.max_entries,
        draw_at=c.draw_at.isoformat() if c.draw_at else None,
    )


def _advance_campaign(
    session: Session,
    campaign: Campaign,
    target_status: str,
    actor_id: uuid.UUID,
    reason: str | None = None,
) -> None:
    """Transition campaign to target_status via the DB trigger.

    Sets app.actor_user_id so the trigger records the correct actor in history.
    Raises HTTP 400 if the transition is invalid (trigger SQLSTATE 23514).
    """
    session.execute(text("SET LOCAL app.actor_user_id = :uid"), {"uid": str(actor_id)})
    if reason:
        session.execute(text("SET LOCAL app.reason = :r"), {"r": reason})
    try:
        campaign.status = target_status
        session.flush()
    except DBAPIError as exc:
        sqlstate = getattr(exc.orig, "sqlstate", None)
        pgerror = str(getattr(exc.orig, "pgerror", exc))
        if sqlstate == "23514":
            raise HTTPException(
                status_code=400,
                detail=pgerror.split("DETAIL:")[0].strip().replace("ERROR:  ", ""),
            ) from exc
        raise


# ── Campaign routes ───────────────────────────────────────────────────────────

@router.get("/campaigns", response_model=list[CampaignOut])
def list_all_campaigns(
    session: Annotated[Session, Depends(get_db)],
    _principal: Annotated[
        Principal,
        Depends(require_roles("ADMIN", "SUPER_ADMIN", "CAMPAIGN_MANAGER", "AUDITOR")),
    ],
) -> list[CampaignOut]:
    campaigns = session.scalars(select(Campaign).order_by(Campaign.created_at.desc())).all()
    return [_campaign_to_out(c, session) for c in campaigns]


@router.post("/campaigns/{campaign_id}/review", response_model=CampaignOut)
def start_review(
    campaign_id: str,
    session: Annotated[Session, Depends(get_db)],
    principal: Annotated[
        Principal,
        Depends(require_roles("ADMIN", "SUPER_ADMIN", "CAMPAIGN_MANAGER")),
    ],
) -> CampaignOut:
    """Move SUBMITTED → UNDER_REVIEW."""
    try:
        cid = uuid.UUID(campaign_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Campaign not found") from None
    c = session.scalar(select(Campaign).where(Campaign.id == cid))
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    _advance_campaign(session, c, "UNDER_REVIEW", principal.user.id)
    session.commit()
    session.refresh(c)
    return _campaign_to_out(c, session)


@router.post("/campaigns/{campaign_id}/approve", response_model=CampaignOut)
def approve_campaign(
    campaign_id: str,
    session: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(require_roles("ADMIN", "SUPER_ADMIN"))],
) -> CampaignOut:
    """Move UNDER_REVIEW → APPROVED.

    The DB trigger records the transition; no manual history insert is needed.
    """
    try:
        cid = uuid.UUID(campaign_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Campaign not found") from None
    c = session.scalar(select(Campaign).where(Campaign.id == cid))
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    _advance_campaign(session, c, "APPROVED", principal.user.id)
    session.commit()
    session.refresh(c)
    return _campaign_to_out(c, session)


@router.post("/campaigns/{campaign_id}/verify-asset", response_model=CampaignOut)
def verify_asset(
    campaign_id: str,
    session: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(require_roles("ADMIN", "SUPER_ADMIN"))],
) -> CampaignOut:
    """Move APPROVED → ASSET_VERIFIED (prize is confirmed in custody)."""
    try:
        cid = uuid.UUID(campaign_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Campaign not found") from None
    c = session.scalar(select(Campaign).where(Campaign.id == cid))
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    _advance_campaign(session, c, "ASSET_VERIFIED", principal.user.id)
    session.commit()
    session.refresh(c)
    return _campaign_to_out(c, session)


@router.post("/campaigns/{campaign_id}/schedule", response_model=CampaignOut)
def schedule_campaign(
    campaign_id: str,
    session: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(require_roles("CAMPAIGN_MANAGER"))],
) -> CampaignOut:
    """Move ASSET_VERIFIED → SCHEDULED."""
    try:
        cid = uuid.UUID(campaign_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Campaign not found") from None
    c = session.scalar(select(Campaign).where(Campaign.id == cid))
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    _advance_campaign(session, c, "SCHEDULED", principal.user.id)
    session.commit()
    session.refresh(c)
    return _campaign_to_out(c, session)


@router.post("/campaigns/{campaign_id}/activate", response_model=CampaignOut)
def activate_campaign(
    campaign_id: str,
    session: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(require_roles("ADMIN", "SUPER_ADMIN"))],
) -> CampaignOut:
    """Move SCHEDULED → ACTIVE.

    The DB trigger enforces that:
      - At least one prize exists
      - The prize asset is VERIFIED with custody evidence (D-04)
      - The entry mode either is FREE/PROMOTIONAL, or has a legal approval row (D-01)
      - A draw with a seed commitment exists
    Any violation is raised as SQLSTATE 23514 and returned as HTTP 400.
    """
    try:
        cid = uuid.UUID(campaign_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Campaign not found") from None
    c = session.scalar(select(Campaign).where(Campaign.id == cid))
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    _advance_campaign(session, c, "ACTIVE", principal.user.id)
    session.commit()
    session.refresh(c)
    return _campaign_to_out(c, session)


@router.post("/campaigns/{campaign_id}/suspend", response_model=CampaignOut)
def suspend_campaign(
    campaign_id: str,
    session: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(require_roles("ADMIN", "SUPER_ADMIN"))],
) -> CampaignOut:
    """Suspend an ACTIVE campaign."""
    try:
        cid = uuid.UUID(campaign_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Campaign not found") from None
    c = session.scalar(select(Campaign).where(Campaign.id == cid))
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    _advance_campaign(session, c, "SUSPENDED", principal.user.id)
    session.commit()
    session.refresh(c)
    return _campaign_to_out(c, session)


# ── Vendor routes ─────────────────────────────────────────────────────────────

@router.get("/vendors", response_model=list[VendorOut])
def list_all_vendors(
    session: Annotated[Session, Depends(get_db)],
    _principal: Annotated[Principal, Depends(require_roles("ADMIN", "SUPER_ADMIN"))],
) -> list[VendorOut]:
    vendors = session.scalars(select(Vendor).order_by(Vendor.created_at.desc())).all()
    return [
        VendorOut(
            id=str(v.id),
            legal_name=v.legal_name,
            display_name=v.display_name,
            status=v.status,
            contact_email=v.contact_email,
        )
        for v in vendors
    ]


@router.get("/draws", response_model=list[DrawOut])
def list_draws(
    session: Annotated[Session, Depends(get_db)],
    _principal: Annotated[
        Principal,
        Depends(require_roles("ADMIN", "SUPER_ADMIN", "AUDITOR")),
    ],
) -> list[DrawOut]:
    draws = session.scalars(select(Draw).order_by(Draw.created_at.desc())).all()
    results: list[DrawOut] = []
    for draw in draws:
        campaign = session.scalar(select(Campaign).where(Campaign.id == draw.campaign_id))
        results.append(
            DrawOut(
                id=str(draw.id),
                campaign_id=str(draw.campaign_id),
                campaign_title=campaign.title if campaign else "Unknown",
                status=draw.status,
                pool_locked_at=draw.pool_locked_at.isoformat() if draw.pool_locked_at else None,
                executed_at=draw.executed_at.isoformat() if draw.executed_at else None,
                planned_entropy_source=draw.planned_entropy_source,
                planned_entropy_round=draw.planned_entropy_round,
            )
        )
    return results


@router.post("/vendors/{vendor_id}/approve", response_model=VendorOut)
def approve_vendor(
    vendor_id: str,
    session: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(require_roles("ADMIN", "SUPER_ADMIN"))],
) -> VendorOut:
    try:
        vid = uuid.UUID(vendor_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Vendor not found") from None
    vendor = session.scalar(select(Vendor).where(Vendor.id == vid))
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    if vendor.status != "PENDING":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve vendor with status '{vendor.status}'",
        )
    vendor.status = "APPROVED"
    vendor.approved_by = principal.user.id
    vendor.approved_at = datetime.now(UTC)
    session.commit()
    session.refresh(vendor)
    return VendorOut(
        id=str(vendor.id),
        legal_name=vendor.legal_name,
        display_name=vendor.display_name,
        status=vendor.status,
        contact_email=vendor.contact_email,
    )
