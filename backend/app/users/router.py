from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.dependencies import Principal, get_current_principal

router = APIRouter(prefix="/users", tags=["users"])


class MeOut(BaseModel):
    id: str
    phone: str | None
    email: str | None
    display_name: str | None
    role: str
    status: str


@router.get("/me", response_model=MeOut)
def current_user(
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> MeOut:
    user = principal.user
    # Primary role for frontend (highest privilege)
    role_priority = ["SUPER_ADMIN", "ADMIN", "CAMPAIGN_MANAGER", "FINANCE",
                     "AUDITOR", "VENDOR", "CUSTOMER_SUPPORT", "PARTICIPANT"]
    roles = principal.roles
    primary_role = next((r for r in role_priority if r in roles), "PARTICIPANT")

    return MeOut(
        id=str(user.id),
        phone=user.phone,
        email=user.email,
        display_name=None,  # TODO: add display_name column in migration
        role=primary_role,
        status=user.status,
    )
