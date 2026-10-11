"""Vendor routes — vendor profile, assets, and campaigns."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.assets.models import Asset
from app.auth.dependencies import Principal, get_current_principal, require_roles
from app.campaigns.models import Campaign, CampaignPrize
from app.core.db import get_db
from app.vendors.models import Vendor, VendorUser

router = APIRouter(prefix="/vendors", tags=["vendors"])


class VendorOut(BaseModel):
    id: str
    legal_name: str
    display_name: str
    status: str
    contact_email: str | None = None
    contact_phone: str | None = None


class AssetOut(BaseModel):
    id: str
    vendor_id: str
    name: str
    description: str | None = None
    declared_value: float
    status: str


class CampaignOut(BaseModel):
    id: str
    title: str
    status: str
    max_entries: int
    draw_at: str | None = None


def _get_vendor_for_user(session: Session, user_id: uuid.UUID) -> Vendor:
    vu = session.scalar(select(VendorUser).where(VendorUser.user_id == user_id))
    if not vu:
        raise HTTPException(status_code=404, detail="No vendor account found")
    vendor = session.scalar(select(Vendor).where(Vendor.id == vu.vendor_id))
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


@router.get("/me", response_model=VendorOut)
def get_my_vendor(
    session: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(require_roles("VENDOR", "ADMIN", "SUPER_ADMIN"))],
) -> VendorOut:
    vendor = _get_vendor_for_user(session, principal.user.id)
    return VendorOut(
        id=str(vendor.id),
        legal_name=vendor.legal_name,
        display_name=vendor.display_name,
        status=vendor.status,
        contact_email=vendor.contact_email,
        contact_phone=vendor.contact_phone,
    )


@router.get("/me/campaigns", response_model=list[CampaignOut])
def get_vendor_campaigns(
    session: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(require_roles("VENDOR", "ADMIN", "SUPER_ADMIN"))],
) -> list[CampaignOut]:
    vendor = _get_vendor_for_user(session, principal.user.id)
    campaigns = session.scalars(
        select(Campaign).where(Campaign.vendor_id == vendor.id).order_by(Campaign.created_at.desc())
    ).all()
    return [
        CampaignOut(
            id=str(c.id),
            title=c.title,
            status=c.status,
            max_entries=c.max_entries,
            draw_at=c.draw_at.isoformat() if c.draw_at else None,
        )
        for c in campaigns
    ]


@router.get("", response_model=list[VendorOut])
def list_vendors(
    session: Annotated[Session, Depends(get_db)],
    _principal: Annotated[Principal, Depends(require_roles("ADMIN", "SUPER_ADMIN", "AUDITOR"))],
) -> list[VendorOut]:
    vendors = session.scalars(select(Vendor).order_by(Vendor.created_at.desc())).all()
    return [
        VendorOut(
            id=str(v.id),
            legal_name=v.legal_name,
            display_name=v.display_name,
            status=v.status,
            contact_email=v.contact_email,
            contact_phone=v.contact_phone,
        )
        for v in vendors
    ]
