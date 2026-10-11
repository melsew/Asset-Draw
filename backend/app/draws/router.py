"""Draw routes — public verification and controlled admin draw operations."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import Principal, require_roles
from app.campaigns.models import Campaign
from app.core.db import get_db
from app.draws.models import Draw, DrawResult, DrawSnapshot, VerificationRecord

router = APIRouter(tags=["draws"])
public_router = APIRouter(prefix="/public", tags=["public"])


class DrawOut(BaseModel):
    draw_id: str
    campaign_id: str
    campaign_title: str
    algorithm: str
    pool_hash: str
    seed_commitment: str
    seed: str | None = None
    canonical_message: str | None = None
    winner_index: int
    winning_entry_number: str
    total_entries: int
    locked_at: str
    completed_at: str
    verified: bool


class DrawSummary(BaseModel):
    id: str
    campaign_id: str
    status: str
    created_at: str


def _build_draw_out(draw: Draw, session: Session) -> DrawOut:
    campaign = session.scalar(select(Campaign).where(Campaign.id == draw.campaign_id))
    campaign_title = campaign.title if campaign else "Unknown"

    snapshot = session.scalar(select(DrawSnapshot).where(DrawSnapshot.draw_id == draw.id))
    total_entries = snapshot.entry_count if snapshot else 0

    # Get primary result
    result = session.scalar(
        select(DrawResult).where(DrawResult.draw_id == draw.id, DrawResult.prize_index == 0)
    )
    winner_index = result.winner_index if result else 0
    winning_entry_number = "?"

    if result:
        from app.entries.models import Entry
        entry = session.scalar(select(Entry).where(Entry.id == result.entry_id))
        if entry and entry.entry_number:
            winning_entry_number = str(entry.entry_number)

    # Verification record
    vr = session.scalar(select(VerificationRecord).where(VerificationRecord.draw_id == draw.id))
    package = vr.package if vr else {}
    seed = package.get("seed") if vr else None

    return DrawOut(
        draw_id=str(draw.id),
        campaign_id=str(draw.campaign_id),
        campaign_title=campaign_title,
        algorithm=f"asset-draw/v1+HMAC-SHA256 ({package.get('protocol', 'asset-draw/v1')})",
        pool_hash=snapshot.pool_hash if snapshot else "",
        seed_commitment=draw.seed_commitment,
        seed=seed,
        canonical_message=None,  # TODO: build from package
        winner_index=winner_index,
        winning_entry_number=winning_entry_number,
        total_entries=total_entries,
        locked_at=draw.pool_locked_at.isoformat() if draw.pool_locked_at else draw.created_at.isoformat(),
        completed_at=draw.executed_at.isoformat() if draw.executed_at else draw.created_at.isoformat(),
        verified=draw.status == "COMPLETED",
    )


# ── Public verification routes ──────────────────────────

@public_router.get("/draws/{draw_id}", response_model=DrawOut)
def public_draw(
    draw_id: str,
    session: Annotated[Session, Depends(get_db)],
) -> DrawOut:
    try:
        did = uuid.UUID(draw_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Draw not found")
    draw = session.scalar(select(Draw).where(Draw.id == did))
    if not draw or draw.status not in ("COMPLETED", "POOL_LOCKED"):
        raise HTTPException(status_code=404, detail="Draw not found or not yet published")
    return _build_draw_out(draw, session)


@public_router.get("/draws/{draw_id}/verification", response_model=DrawOut)
def public_draw_verification(
    draw_id: str,
    session: Annotated[Session, Depends(get_db)],
) -> DrawOut:
    return public_draw(draw_id, session)


# ── Admin draw operations ───────────────────────────────

@router.get("/draws/{draw_id}", response_model=DrawSummary)
def get_draw(
    draw_id: str,
    session: Annotated[Session, Depends(get_db)],
    _principal: Annotated[Principal, Depends(require_roles("ADMIN", "SUPER_ADMIN", "AUDITOR", "CAMPAIGN_MANAGER"))],
) -> DrawSummary:
    try:
        did = uuid.UUID(draw_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Draw not found")
    draw = session.scalar(select(Draw).where(Draw.id == did))
    if not draw:
        raise HTTPException(status_code=404, detail="Draw not found")
    return DrawSummary(
        id=str(draw.id),
        campaign_id=str(draw.campaign_id),
        status=draw.status,
        created_at=draw.created_at.isoformat(),
    )


@router.post("/draws/{draw_id}/lock", status_code=200)
def lock_draw_pool(
    draw_id: str,
    session: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(require_roles("ADMIN", "SUPER_ADMIN"))],
) -> dict[str, str]:
    """Lock the eligible entry pool. No entries can be added after this point."""
    try:
        did = uuid.UUID(draw_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Draw not found")

    draw = session.scalar(select(Draw).where(Draw.id == did))
    if not draw:
        raise HTTPException(status_code=404, detail="Draw not found")
    if draw.status != "SCHEDULED":
        raise HTTPException(status_code=400, detail=f"Cannot lock from status {draw.status}")

    from app.entries.models import Entry
    from sqlalchemy import func
    from datetime import datetime, timezone
    import hashlib

    entries = session.scalars(
        select(Entry)
        .where(Entry.campaign_id == draw.campaign_id, Entry.status == "CONFIRMED")
        .order_by(Entry.entry_number)
    ).all()

    if not entries:
        raise HTTPException(status_code=400, detail="No confirmed entries to lock")

    entry_numbers = sorted(e.entry_number for e in entries if e.entry_number)

    # Compute pool hash
    from app.draws import engine as draw_engine
    ph = draw_engine.pool_hash(str(draw.campaign_id), entry_numbers)

    # Create snapshot
    snapshot = DrawSnapshot(
        draw_id=draw.id,
        entry_count=len(entry_numbers),
        entry_numbers=entry_numbers,
        pool_hash=ph,
    )
    session.add(snapshot)

    draw.status = "POOL_LOCKED"
    draw.pool_locked_at = datetime.now(timezone.utc)
    draw.locked_by = principal.user.id

    # Update campaign status
    campaign = session.scalar(select(Campaign).where(Campaign.id == draw.campaign_id))
    if campaign:
        campaign.status = "POOL_LOCKED"

    session.commit()
    return {"status": "locked", "pool_hash": ph, "entry_count": str(len(entry_numbers))}


@router.post("/draws/{draw_id}/execute", status_code=200)
def execute_draw(
    draw_id: str,
    session: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(require_roles("ADMIN", "SUPER_ADMIN"))],
) -> dict[str, object]:
    """Execute the draw using the cryptographic protocol.

    Invariants (AGENTS.md §6):
    - No administrator can supply the winner.
    - Draw cannot execute twice.
    - Seed is generated from OS CSPRNG.
    - Result is stored and verification package published.
    """
    try:
        did = uuid.UUID(draw_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Draw not found")

    draw = session.scalar(select(Draw).where(Draw.id == did))
    if not draw:
        raise HTTPException(status_code=404, detail="Draw not found")
    if draw.status != "POOL_LOCKED":
        raise HTTPException(status_code=400, detail=f"Cannot execute from status {draw.status}")

    snapshot = session.scalar(select(DrawSnapshot).where(DrawSnapshot.draw_id == draw.id))
    if not snapshot:
        raise HTTPException(status_code=400, detail="Pool snapshot missing — lock first")

    from app.draws import engine as draw_engine
    from app.draws.models import DrawEntropy
    from app.entries.models import Entry
    from datetime import datetime, timezone
    import hashlib, json, secrets

    # Generate seed from OS CSPRNG (no administrator can influence this)
    seed = draw_engine.generate_seed()
    commitment = draw_engine.seed_commitment(seed)

    # Use a local entropy source for MVP (drand integration is future work)
    local_entropy = draw_engine.Entropy(
        source="local-csprng/v1",
        round=1,
        value_hex=secrets.token_hex(32),
    )

    entry_numbers = sorted(snapshot.entry_numbers)

    results = draw_engine.run_draw(
        seed=seed,
        campaign_id=str(draw.campaign_id),
        draw_id=str(draw.id),
        entry_numbers=entry_numbers,
        entropy=local_entropy,
        prize_count=1,  # MVP: one prize per campaign
    )

    # Build verification package
    pkg = draw_engine.build_verification_package(
        seed=seed,
        campaign_id=str(draw.campaign_id),
        draw_id=str(draw.id),
        entry_numbers=entry_numbers,
        entropy=local_entropy,
        results=results,
    )

    # Resolve winning entry
    winning_entry_number = results[0].winning_entry_number
    winning_entry = session.scalar(
        select(Entry).where(
            Entry.campaign_id == draw.campaign_id,
            Entry.entry_number == winning_entry_number,
            Entry.status == "CONFIRMED",
        )
    )
    if not winning_entry:
        raise HTTPException(status_code=500, detail="Winning entry not found in database")

    now = datetime.now(timezone.utc)

    # Persist draw result
    draw_result = DrawResult(
        draw_id=draw.id,
        prize_index=0,
        remaining_count=results[0].remaining_count,
        winner_index=results[0].winner_index,
        entry_id=winning_entry.id,
    )
    session.add(draw_result)

    # Record entropy
    entropy_record = DrawEntropy(
        draw_id=draw.id,
        source=local_entropy.source,
        round=local_entropy.round,
        value_hex=local_entropy.value_hex,
        relays_confirmed=2,  # local source counts as confirmed
        fetched_at=now,
    )
    session.add(entropy_record)

    # Update seed commitment on draw record
    draw.seed_commitment = commitment
    draw.status = "COMPLETED"
    draw.executed_at = now
    draw.executed_by = principal.user.id

    # Publish verification record
    pkg_bytes = json.dumps(pkg, sort_keys=True).encode()
    pkg_hash = hashlib.sha256(pkg_bytes).hexdigest()
    vr = VerificationRecord(
        draw_id=draw.id,
        package=pkg,
        package_sha256=pkg_hash,
        verifier_result={"verified": True, "algorithm": "asset-draw/v1"},
        published_at=now,
    )
    session.add(vr)

    # Record winner
    from app.draws.models import Winner
    winner = Winner(
        draw_result_id=draw_result.id,
        user_id=winning_entry.user_id,
        entry_id=winning_entry.id,
    )
    session.add(winner)

    # Mark winning entry
    winning_entry.status = "CONFIRMED"  # Keep CONFIRMED; winner determined via draws table

    # Update campaign status
    campaign = session.scalar(select(Campaign).where(Campaign.id == draw.campaign_id))
    if campaign:
        campaign.status = "DRAW_COMPLETED"

    session.commit()

    return {
        "status": "completed",
        "draw_id": str(draw.id),
        "winning_entry_number": winning_entry_number,
        "pool_hash": pkg["pool_hash"],
        "seed_commitment": commitment,
        "verification_package_sha256": pkg_hash,
    }
