"""Liveness and readiness endpoints (spec section 28: API, database and worker health)."""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core import db, redis_client
from app.core.demo_store import demo_health_payload, is_demo_mode

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def live() -> dict[str, str]:
    """Process is up. Does not touch dependencies."""
    return {"status": "ok"}


@router.get("/ready")
def ready() -> JSONResponse:
    """Ready only if PostgreSQL and Redis are reachable."""
    if is_demo_mode():
        return JSONResponse(status_code=200, content=demo_health_payload())

    checks: dict[str, str] = {}
    for name, fn in (("database", db.check_database), ("redis", redis_client.check_redis)):
        try:
            fn()
            checks[name] = "ok"
        except Exception:  # noqa: BLE001 - report any failure as unavailable, never leak details
            checks[name] = "unavailable"
    healthy = all(v == "ok" for v in checks.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "ok" if healthy else "degraded", "checks": checks},
    )
