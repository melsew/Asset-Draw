"""Asset routes — vendor asset registration and admin verification."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.assets.models import Asset
from app.auth.dependencies import Principal, get_current_principal, require_roles
from app.core.db import get_db
from app.vendors.models import VendorUser

router = APIRouter(prefix="/assets", tags=["assets"])


class AssetOut(BaseModel):
    id: str
    vendor_id: str
    name: str
    description: str | None = None
    declared_value: float
    status: str


class AssetCreateIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = None
    declared_value: float = Field(..., gt=0)


@router.get("", response_model=list[AssetOut])
def list_my_assets(
    session: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(require_roles("VENDOR", "ADMIN", "SUPER_ADMIN"))],
) -> list[AssetOut]:
    vu = session.scalar(select(VendorUser).where(VendorUser.user_id == principal.user.id))
    if not vu:
        return []
    assets = session.scalars(
        select(Asset).where(Asset.vendor_id == vu.vendor_id).order_by(Asset.created_at.desc())
    ).all()
    return [
        AssetOut(
            id=str(a.id),
            vendor_id=str(a.vendor_id),
            name=a.name,
            description=a.description,
            declared_value=float(a.declared_value),
            status=a.status,
        )
        for a in assets
    ]


@router.post("", response_model=AssetOut, status_code=status.HTTP_201_CREATED)
def create_asset(
    body: AssetCreateIn,
    session: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(require_roles("VENDOR", "ADMIN", "SUPER_ADMIN"))],
) -> AssetOut:
    vu = session.scalar(select(VendorUser).where(VendorUser.user_id == principal.user.id))
    if not vu:
        raise HTTPException(status_code=403, detail="No vendor account found")

    from decimal import Decimal
    asset = Asset(
        vendor_id=vu.vendor_id,
        name=body.name,
        description=body.description,
        declared_value=Decimal(str(body.declared_value)),
        currency="ETB",
        status="DRAFT",
    )
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return AssetOut(
        id=str(asset.id),
        vendor_id=str(asset.vendor_id),
        name=asset.name,
        description=asset.description,
        declared_value=float(asset.declared_value),
        status=asset.status,
    )
