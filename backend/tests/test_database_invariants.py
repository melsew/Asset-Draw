import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from threading import Barrier

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import Connection, Engine, make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from alembic import command
from app.audit.models import AuditLog
from app.auth.bootstrap_admin import BootstrapError, bootstrap_first_super_admin
from app.auth.models import StaffMFA
from app.auth.security import decode_scoped_token, decrypt_totp_secret, verify_password
from app.auth.services import roles_for_user
from app.core.config import get_settings
from app.users.models import User

BACKEND_ROOT = Path(__file__).resolve().parents[1]
APPEND_ONLY_MUTATIONS = (
    ("audit_logs", "id"),
    ("draw_snapshots", "id"),
    ("draw_entropy", "draw_id"),
    ("draw_results", "id"),
    ("verification_records", "id"),
    ("winners", "id"),
    ("asset_verifications", "id"),
    ("payment_events", "id"),
    ("campaign_status_history", "id"),
    ("prize_fulfillment_history", "id"),
)


@pytest.fixture(scope="session")
def postgres_engine() -> Engine:
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.fail("TEST_DATABASE_URL must point to an isolated PostgreSQL test database")
    database_name = make_url(database_url).database or ""
    if "test" not in database_name.lower():
        pytest.fail("TEST_DATABASE_URL database name must contain 'test'")

    previous_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    get_settings.cache_clear()
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, "head")
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        yield engine
    finally:
        engine.dispose()
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url
        get_settings.cache_clear()


@pytest.fixture
def db(postgres_engine: Engine) -> Connection:
    connection = postgres_engine.connect()
    transaction = connection.begin()
    try:
        yield connection
    finally:
        transaction.rollback()
        connection.close()


def assert_sqlstate(
    connection: Connection,
    statement: str,
    parameters: dict[str, object] | None = None,
    sqlstate: str = "23514",
) -> None:
    with pytest.raises(DBAPIError) as error:
        with connection.begin_nested():
            connection.execute(text(statement), parameters or {})
    assert getattr(error.value.orig, "sqlstate", None) == sqlstate


def add_user(connection: Connection) -> uuid.UUID:
    user_id = uuid.uuid4()
    connection.execute(
        text("INSERT INTO users (id, email) VALUES (:id, :email)"),
        {"id": user_id, "email": f"{user_id}@example.test"},
    )
    return user_id


def make_environment(
    connection: Connection,
    *,
    entry_mode: str = "PROMOTIONAL",
    max_entries: int = 5,
    per_user_limit: int = 5,
    with_draw: bool = True,
    verified_asset: bool = True,
) -> dict[str, uuid.UUID]:
    actor_id = add_user(connection)
    vendor_id = uuid.uuid4()
    connection.execute(
        text(
            "INSERT INTO vendors (id, legal_name, display_name, status) "
            "VALUES (:id, 'Test Vendor LLC', 'Test Vendor', 'APPROVED')"
        ),
        {"id": vendor_id},
    )
    asset_id = uuid.uuid4()
    connection.execute(
        text(
            "INSERT INTO assets "
            "(id, vendor_id, name, declared_value, status) "
            "VALUES (:id, :vendor_id, 'Test Prize', :value, :status)"
        ),
        {
            "id": asset_id,
            "vendor_id": vendor_id,
            "value": Decimal("100.00"),
            "status": "VERIFIED" if verified_asset else "DRAFT",
        },
    )
    if verified_asset:
        connection.execute(
            text(
                "INSERT INTO asset_verifications "
                "(asset_id, verified_by, result, custody_type, evidence_ref) "
                "VALUES (:asset_id, :actor_id, 'APPROVED', 'ESCROW', 'test-evidence')"
            ),
            {"asset_id": asset_id, "actor_id": actor_id},
        )

    campaign_id = uuid.uuid4()
    now = datetime.now(UTC)
    connection.execute(
        text(
            "INSERT INTO campaigns "
            "(id, vendor_id, title, description, entry_mode, entry_price, max_entries, "
            "per_user_limit, start_at, end_at, draw_at, created_by) "
            "VALUES (:id, :vendor_id, 'Test Campaign', 'Test campaign rules', :mode, :price, "
            ":capacity, :user_limit, :start_at, :end_at, :draw_at, :actor_id)"
        ),
        {
            "id": campaign_id,
            "vendor_id": vendor_id,
            "mode": entry_mode,
            "price": Decimal("1.00") if entry_mode in ("PURCHASE", "PAID_ENTRY") else None,
            "capacity": max_entries,
            "user_limit": per_user_limit,
            "start_at": now - timedelta(minutes=1),
            "end_at": now + timedelta(days=1),
            "draw_at": now + timedelta(days=2),
            "actor_id": actor_id,
        },
    )
    connection.execute(
        text("INSERT INTO campaign_prizes (campaign_id, prize_index, asset_id) VALUES (:campaign, 0, :asset)"),
        {"campaign": campaign_id, "asset": asset_id},
    )
    draw_id = uuid.uuid4()
    if with_draw:
        connection.execute(
            text(
                "INSERT INTO draws (id, campaign_id, seed_commitment) "
                "VALUES (:id, :campaign_id, :commitment)"
            ),
            {"id": draw_id, "campaign_id": campaign_id, "commitment": "a" * 64},
        )
    return {
        "actor_id": actor_id,
        "vendor_id": vendor_id,
        "asset_id": asset_id,
        "campaign_id": campaign_id,
        "draw_id": draw_id,
    }


def advance_to_scheduled(connection: Connection, campaign_id: uuid.UUID) -> None:
    for status in ("SUBMITTED", "UNDER_REVIEW", "APPROVED", "ASSET_VERIFIED", "SCHEDULED"):
        connection.execute(
            text("UPDATE campaigns SET status = :status WHERE id = :id"),
            {"status": status, "id": campaign_id},
        )


def activate(connection: Connection, campaign_id: uuid.UUID) -> None:
    advance_to_scheduled(connection, campaign_id)
    connection.execute(
        text("UPDATE campaigns SET status = 'ACTIVE' WHERE id = :id"), {"id": campaign_id}
    )


def lock_campaign(connection: Connection, campaign_id: uuid.UUID) -> None:
    connection.execute(
        text("UPDATE campaigns SET status = 'ENTRY_CLOSED' WHERE id = :id"),
        {"id": campaign_id},
    )
    connection.execute(
        text("UPDATE campaigns SET status = 'POOL_LOCKED' WHERE id = :id"),
        {"id": campaign_id},
    )


def add_pending_entry(
    connection: Connection,
    campaign_id: uuid.UUID,
    user_id: uuid.UUID,
) -> uuid.UUID:
    entry_id = uuid.uuid4()
    connection.execute(
        text(
            "INSERT INTO entries "
            "(id, campaign_id, user_id, status, expires_at, source_type, source_reference) "
            "VALUES (:id, :campaign, :user, 'PENDING', now() + interval '5 minutes', 'DIRECT', :ref)"
        ),
        {"id": entry_id, "campaign": campaign_id, "user": user_id, "ref": str(entry_id)},
    )
    return entry_id


def confirm_entry(connection: Connection, entry_id: uuid.UUID) -> int:
    return connection.execute(
        text("UPDATE entries SET status = 'CONFIRMED' WHERE id = :id RETURNING entry_number"),
        {"id": entry_id},
    ).scalar_one()


def add_snapshot_and_entropy(
    connection: Connection,
    draw_id: uuid.UUID,
    entry_numbers: list[int],
) -> None:
    snapshot_id = uuid.uuid4()
    connection.execute(
        text(
            "INSERT INTO draw_snapshots "
            "(id, draw_id, entry_count, entry_numbers, pool_hash) "
            "VALUES (:id, :draw, :count, CAST(:numbers AS integer[]), :hash)"
        ),
        {
            "id": snapshot_id,
            "draw": draw_id,
            "count": len(entry_numbers),
            "numbers": entry_numbers,
            "hash": "b" * 64,
        },
    )
    connection.execute(
        text(
            "INSERT INTO draw_entropy "
            "(draw_id, source, round, value_hex, relays_confirmed, fetched_at) "
            "VALUES (:draw, 'drand:test', 1, :value, 2, now())"
        ),
        {"draw": draw_id, "value": "ab" * 32},
    )


def add_draw_result(
    connection: Connection,
    draw_id: uuid.UUID,
    entry_id: uuid.UUID,
    prize_index: int = 0,
) -> uuid.UUID:
    result_id = uuid.uuid4()
    connection.execute(
        text(
            "INSERT INTO draw_results "
            "(id, draw_id, prize_index, remaining_count, winner_index, entry_id) "
            "VALUES (:id, :draw, :prize_index, 1, 0, :entry)"
        ),
        {"id": result_id, "draw": draw_id, "prize_index": prize_index, "entry": entry_id},
    )
    return result_id


def test_t1_campaign_transitions_are_checked_and_recorded(db: Connection) -> None:
    environment = make_environment(db)
    campaign_id = environment["campaign_id"]

    assert_sqlstate(
        db,
        "UPDATE campaigns SET status = 'APPROVED' WHERE id = :id",
        {"id": campaign_id},
    )
    db.execute(
        text("UPDATE campaigns SET status = 'SUBMITTED' WHERE id = :id"),
        {"id": campaign_id},
    )
    history_count = db.execute(
        text("SELECT count(*) FROM campaign_status_history WHERE campaign_id = :id"),
        {"id": campaign_id},
    ).scalar_one()
    assert history_count == 1

    direct_id = uuid.uuid4()
    now = datetime.now(UTC)
    assert_sqlstate(
        db,
        "INSERT INTO campaigns "
        "(id, vendor_id, title, description, entry_mode, max_entries, start_at, end_at, draw_at, status, created_by) "
        "VALUES (:id, :vendor, 'Bypass', 'Bypass', 'FREE', 2, :start, :end, :draw, 'ACTIVE', :actor)",
        {
            "id": direct_id,
            "vendor": environment["vendor_id"],
            "start": now,
            "end": now + timedelta(days=1),
            "draw": now + timedelta(days=2),
            "actor": environment["actor_id"],
        },
    )


def test_t2_activation_requires_verified_assets_draw_and_entry_mode_approval(db: Connection) -> None:
    no_draw = make_environment(db, with_draw=False)
    advance_to_scheduled(db, no_draw["campaign_id"])
    assert_sqlstate(
        db,
        "UPDATE campaigns SET status = 'ACTIVE' WHERE id = :id",
        {"id": no_draw["campaign_id"]},
    )

    no_evidence = make_environment(db, verified_asset=False)
    advance_to_scheduled(db, no_evidence["campaign_id"])
    assert_sqlstate(
        db,
        "UPDATE campaigns SET status = 'ACTIVE' WHERE id = :id",
        {"id": no_evidence["campaign_id"]},
    )

    paid = make_environment(db, entry_mode="PURCHASE")
    advance_to_scheduled(db, paid["campaign_id"])
    assert_sqlstate(
        db,
        "UPDATE campaigns SET status = 'ACTIVE' WHERE id = :id",
        {"id": paid["campaign_id"]},
    )
    db.execute(
        text(
            "INSERT INTO entry_mode_approvals "
            "(campaign_id, entry_mode, approved_by, approved_at, legal_reference) "
            "VALUES (:campaign, 'PURCHASE', :actor, now(), 'legal-approval-test')"
        ),
        {"campaign": paid["campaign_id"], "actor": paid["actor_id"]},
    )
    db.execute(
        text("UPDATE campaigns SET status = 'ACTIVE' WHERE id = :id"),
        {"id": paid["campaign_id"]},
    )


def test_t3_entries_cannot_change_after_pool_lock(db: Connection) -> None:
    environment = make_environment(db)
    activate(db, environment["campaign_id"])
    user_id = add_user(db)
    entry_id = add_pending_entry(db, environment["campaign_id"], user_id)
    lock_campaign(db, environment["campaign_id"])

    assert_sqlstate(
        db,
        "INSERT INTO entries (campaign_id, user_id, status, source_type) "
        "VALUES (:campaign, :user, 'PENDING', 'DIRECT')",
        {"campaign": environment["campaign_id"], "user": user_id},
        "55000",
    )
    assert_sqlstate(
        db,
        "UPDATE entries SET status = 'CANCELLED' WHERE id = :id",
        {"id": entry_id},
        "55000",
    )
    assert_sqlstate(db, "DELETE FROM entries WHERE id = :id", {"id": entry_id}, "55000")


def test_t4_capacity_and_entry_numbers_are_database_allocated(db: Connection) -> None:
    capacity = make_environment(db, max_entries=1, per_user_limit=3)
    activate(db, capacity["campaign_id"])
    first_user = add_user(db)
    first_entry = add_pending_entry(db, capacity["campaign_id"], first_user)
    assert_sqlstate(
        db,
        "INSERT INTO entries (campaign_id, user_id, status, source_type) "
        "VALUES (:campaign, :user, 'PENDING', 'DIRECT')",
        {"campaign": capacity["campaign_id"], "user": add_user(db)},
    )
    assert confirm_entry(db, first_entry) == 1
    assert_sqlstate(
        db,
        "INSERT INTO entries (campaign_id, user_id, entry_number, status, source_type) "
        "VALUES (:campaign, :user, 77, 'CONFIRMED', 'DIRECT')",
        {"campaign": capacity["campaign_id"], "user": add_user(db)},
    )

    user_limited = make_environment(db, max_entries=4, per_user_limit=1)
    activate(db, user_limited["campaign_id"])
    participant = add_user(db)
    add_pending_entry(db, user_limited["campaign_id"], participant)
    assert_sqlstate(
        db,
        "INSERT INTO entries (campaign_id, user_id, status, source_type) "
        "VALUES (:campaign, :user, 'PENDING', 'DIRECT')",
        {"campaign": user_limited["campaign_id"], "user": participant},
    )


def test_t4_concurrent_reservations_do_not_exceed_capacity(postgres_engine: Engine) -> None:
    with postgres_engine.begin() as connection:
        environment = make_environment(connection, max_entries=1, per_user_limit=1)
        activate(connection, environment["campaign_id"])
        users = (add_user(connection), add_user(connection))

    barrier = Barrier(2)

    def reserve(user_id: uuid.UUID) -> bool:
        try:
            with postgres_engine.begin() as connection:
                barrier.wait(timeout=10)
                add_pending_entry(connection, environment["campaign_id"], user_id)
            return True
        except DBAPIError:
            return False

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(reserve, users))

    assert sum(results) == 1
    with postgres_engine.connect() as connection:
        active_entries = connection.execute(
            text(
                "SELECT count(*) FROM entries WHERE campaign_id = :campaign "
                "AND status IN ('PENDING', 'CONFIRMED')"
            ),
            {"campaign": environment["campaign_id"]},
        ).scalar_one()
    assert active_entries == 1


def test_t5_append_only_evidence_rejects_update_delete_and_truncate(db: Connection) -> None:
    environment = make_environment(db)
    campaign_id = environment["campaign_id"]
    draw_id = environment["draw_id"]
    activate(db, campaign_id)
    entry_id = add_pending_entry(db, campaign_id, add_user(db))
    entry_number = confirm_entry(db, entry_id)
    lock_campaign(db, campaign_id)
    add_snapshot_and_entropy(db, draw_id, [entry_number])
    result_id = add_draw_result(db, draw_id, entry_id)

    audit_id = uuid.uuid4()
    db.execute(
        text(
            "INSERT INTO audit_logs "
            "(id, actor_type, action, entity_type, metadata, row_hash) "
            "VALUES (:id, 'SYSTEM', 'test', 'Campaign', '{}'::jsonb, :hash)"
        ),
        {"id": audit_id, "hash": "f" * 64},
    )
    payment_event_id = uuid.uuid4()
    db.execute(
        text(
            "INSERT INTO payment_events "
            "(id, provider, event_type, payload_sha256) "
            "VALUES (:id, 'test', 'test', :hash)"
        ),
        {"id": payment_event_id, "hash": "c" * 64},
    )
    verification_id = uuid.uuid4()
    db.execute(
        text(
            "INSERT INTO verification_records "
            "(id, draw_id, package, package_sha256, verifier_result, published_at) "
            "VALUES (:id, :draw, '{}'::jsonb, :hash, '{}'::jsonb, now())"
        ),
        {"id": verification_id, "draw": draw_id, "hash": "d" * 64},
    )
    winner_id = uuid.uuid4()
    db.execute(
        text(
            "INSERT INTO winners (id, draw_result_id, user_id, entry_id) "
            "VALUES (:id, :result, :user, :entry)"
        ),
        {
            "id": winner_id,
            "result": result_id,
            "user": db.execute(text("SELECT user_id FROM entries WHERE id = :id"), {"id": entry_id}).scalar_one(),
            "entry": entry_id,
        },
    )
    fulfillment_id = uuid.uuid4()
    db.execute(
        text("INSERT INTO prize_fulfillments (id, winner_id) VALUES (:id, :winner)"),
        {"id": fulfillment_id, "winner": winner_id},
    )
    history_id = uuid.uuid4()
    db.execute(
        text(
            "INSERT INTO prize_fulfillment_history (id, fulfillment_id, status) "
            "VALUES (:id, :fulfillment, 'PENDING')"
        ),
        {"id": history_id, "fulfillment": fulfillment_id},
    )

    rows = {
        "audit_logs": audit_id,
        "draw_snapshots": db.execute(
            text("SELECT id FROM draw_snapshots WHERE draw_id = :id"), {"id": draw_id}
        ).scalar_one(),
        "draw_entropy": draw_id,
        "draw_results": result_id,
        "verification_records": verification_id,
        "winners": winner_id,
        "asset_verifications": db.execute(
            text("SELECT id FROM asset_verifications WHERE asset_id = :id"),
            {"id": environment["asset_id"]},
        ).scalar_one(),
        "payment_events": payment_event_id,
        "campaign_status_history": db.execute(
            text("SELECT id FROM campaign_status_history WHERE campaign_id = :id LIMIT 1"),
            {"id": campaign_id},
        ).scalar_one(),
        "prize_fulfillment_history": history_id,
    }
    update_columns = {
        "audit_logs": "action = action",
        "draw_snapshots": "entry_count = entry_count",
        "draw_entropy": "source = source",
        "draw_results": "created_at = created_at",
        "verification_records": "published_at = published_at",
        "winners": "created_at = created_at",
        "asset_verifications": "notes = notes",
        "payment_events": "event_type = event_type",
        "campaign_status_history": "reason = reason",
        "prize_fulfillment_history": "status = status",
    }
    keys = {
        "draw_entropy": "draw_id",
    }
    for table, row_id in rows.items():
        key_column = keys.get(table, "id")
        assert_sqlstate(
            db,
            f"UPDATE {table} SET {update_columns[table]} WHERE {key_column} = :id",
            {"id": row_id},
            "55000",
        )
        assert_sqlstate(
            db, f"DELETE FROM {table} WHERE {key_column} = :id", {"id": row_id}, "55000"
        )
        assert_sqlstate(db, f"TRUNCATE TABLE {table} CASCADE", sqlstate="55000")


def test_t6_draw_commitment_pool_lock_and_stage_are_write_once(db: Connection) -> None:
    environment = make_environment(db)
    draw_id = environment["draw_id"]
    assert_sqlstate(
        db,
        "UPDATE draws SET seed_commitment = :hash WHERE id = :id",
        {"id": draw_id, "hash": "b" * 64},
        "55000",
    )
    db.execute(
        text(
            "UPDATE draws SET pool_locked_at = now(), planned_entropy_source = 'drand:test', "
            "planned_entropy_round = 1 WHERE id = :id"
        ),
        {"id": draw_id},
    )
    assert_sqlstate(
        db,
        "UPDATE draws SET planned_entropy_round = 2 WHERE id = :id",
        {"id": draw_id},
        "55000",
    )
    db.execute(
        text("UPDATE draws SET stage = 'ENTROPY_FETCHED' WHERE id = :id"),
        {"id": draw_id},
    )
    assert_sqlstate(
        db,
        "UPDATE draws SET stage = 'NONE' WHERE id = :id",
        {"id": draw_id},
    )


def test_t7_draw_result_requires_snapshot_entropy_and_snapshot_entry(db: Connection) -> None:
    environment = make_environment(db)
    activate(db, environment["campaign_id"])
    first_entry = add_pending_entry(db, environment["campaign_id"], add_user(db))
    first_number = confirm_entry(db, first_entry)
    second_entry = add_pending_entry(db, environment["campaign_id"], add_user(db))
    confirm_entry(db, second_entry)
    lock_campaign(db, environment["campaign_id"])

    result_id = uuid.uuid4()
    result_sql = (
        "INSERT INTO draw_results "
        "(id, draw_id, prize_index, remaining_count, winner_index, entry_id) "
        "VALUES (:id, :draw, 0, 1, 0, :entry)"
    )
    assert_sqlstate(
        db,
        result_sql,
        {"id": result_id, "draw": environment["draw_id"], "entry": first_entry},
    )

    snapshot_id = uuid.uuid4()
    db.execute(
        text(
            "INSERT INTO draw_snapshots "
            "(id, draw_id, entry_count, entry_numbers, pool_hash) "
            "VALUES (:id, :draw, 1, CAST(:numbers AS integer[]), :hash)"
        ),
        {
            "id": snapshot_id,
            "draw": environment["draw_id"],
            "numbers": [first_number],
            "hash": "b" * 64,
        },
    )
    assert_sqlstate(
        db,
        result_sql,
        {"id": result_id, "draw": environment["draw_id"], "entry": first_entry},
    )
    db.execute(
        text(
            "INSERT INTO draw_entropy "
            "(draw_id, source, round, value_hex, relays_confirmed, fetched_at) "
            "VALUES (:draw, 'drand:test', 1, :value, 2, now())"
        ),
        {"draw": environment["draw_id"], "value": "ab" * 32},
    )
    assert_sqlstate(
        db,
        result_sql,
        {"id": result_id, "draw": environment["draw_id"], "entry": second_entry},
    )
    db.execute(
        text(result_sql),
        {"id": result_id, "draw": environment["draw_id"], "entry": first_entry},
    )


def test_t8_winner_must_match_selected_result(db: Connection) -> None:
    environment = make_environment(db)
    activate(db, environment["campaign_id"])
    selected_entry = add_pending_entry(db, environment["campaign_id"], add_user(db))
    selected_number = confirm_entry(db, selected_entry)
    other_entry = add_pending_entry(db, environment["campaign_id"], add_user(db))
    confirm_entry(db, other_entry)
    lock_campaign(db, environment["campaign_id"])
    add_snapshot_and_entropy(db, environment["draw_id"], [selected_number])
    result_id = add_draw_result(db, environment["draw_id"], selected_entry)
    other_user = db.execute(
        text("SELECT user_id FROM entries WHERE id = :id"), {"id": other_entry}
    ).scalar_one()

    assert_sqlstate(
        db,
        "INSERT INTO winners (draw_result_id, user_id, entry_id) VALUES (:result, :user, :entry)",
        {"result": result_id, "user": other_user, "entry": other_entry},
    )


def test_t9_audit_hash_is_server_generated_and_chained(db: Connection) -> None:
    first_id = uuid.uuid4()
    db.execute(
        text(
            "INSERT INTO audit_logs "
            "(id, actor_type, action, entity_type, metadata, prev_hash, row_hash) "
            "VALUES (:id, 'SYSTEM', 'first', 'Test', '{}'::jsonb, :prev, :hash)"
        ),
        {"id": first_id, "prev": "e" * 64, "hash": "f" * 64},
    )
    first = db.execute(
        text("SELECT seq, prev_hash, row_hash FROM audit_logs WHERE id = :id"),
        {"id": first_id},
    ).one()
    assert first.prev_hash == "0" * 64
    assert first.row_hash != "f" * 64

    verified = db.execute(
        text(
            "SELECT a.row_hash = encode(digest(convert_to("
            "a.prev_hash || E'\\n' || public.audit_canonical_row(a), 'UTF8'), 'sha256'), 'hex') "
            "FROM audit_logs a WHERE a.id = :id"
        ),
        {"id": first_id},
    ).scalar_one()
    assert verified is True

    second_id = uuid.uuid4()
    db.execute(
        text(
            "INSERT INTO audit_logs (id, actor_type, action, entity_type, metadata, row_hash) "
            "VALUES (:id, 'SYSTEM', 'second', 'Test', '{}'::jsonb, :hash)"
        ),
        {"id": second_id, "hash": "f" * 64},
    )
    second = db.execute(
        text("SELECT seq, prev_hash FROM audit_logs WHERE id = :id"),
        {"id": second_id},
    ).one()
    assert second.seq > first.seq
    assert second.prev_hash == first.row_hash
    assert_sqlstate(
        db,
        "UPDATE audit_logs SET row_hash = :hash WHERE id = :id",
        {"id": first_id, "hash": "0" * 64},
        "55000",
    )


def test_app_api_cannot_read_draw_secrets_or_write_draw_inputs(db: Connection) -> None:
    environment = make_environment(db)
    db.execute(
        text(
            "INSERT INTO draw_secrets (draw_id, seed_ciphertext, key_id) "
            "VALUES (:draw, decode('abcd', 'hex'), 'test-key')"
        ),
        {"draw": environment["draw_id"]},
    )
    protected_operations = (
        "SELECT * FROM draw_secrets",
        "UPDATE draws SET seed_commitment = repeat('b', 64) WHERE id = :draw",
        "UPDATE campaign_counters SET next_entry_number = 99 WHERE campaign_id = :campaign",
    )
    for operation in protected_operations:
        with pytest.raises(DBAPIError) as error:
            with db.begin_nested():
                db.execute(text("SET LOCAL ROLE app_api"))
                db.execute(
                    text(operation),
                    {"draw": environment["draw_id"], "campaign": environment["campaign_id"]},
                )
        assert getattr(error.value.orig, "sqlstate", None) == "42501"


def test_first_super_admin_bootstrap_is_audited_one_time_and_requires_mfa(
    db: Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTH_SECRET_KEY", "test-signing-key-that-is-at-least-32-bytes")
    monkeypatch.setenv("AUTH_ENCRYPTION_KEY", "test-encryption-key-that-is-at-least-32-bytes")
    get_settings.cache_clear()
    try:
        with Session(bind=db, join_transaction_mode="create_savepoint") as session:
            result = bootstrap_first_super_admin(
                session,
                "Owner@example.test",
                "test-owner-password-123",
            )
            owner = session.get(User, result.user_id)
            staff_mfa = session.get(StaffMFA, result.user_id)
            audit = session.scalar(
                select(AuditLog).where(
                    AuditLog.action == "INITIAL_SUPER_ADMIN_BOOTSTRAPPED",
                    AuditLog.entity_id == result.user_id,
                )
            )

            assert owner is not None
            assert owner.email == "owner@example.test"
            assert owner.password_hash is not None
            assert verify_password(owner.password_hash, "test-owner-password-123")
            assert roles_for_user(session, result.user_id) == ["SUPER_ADMIN"]
            assert staff_mfa is not None
            assert staff_mfa.enabled_at is None
            assert len(decrypt_totp_secret(staff_mfa.totp_secret_encrypted)) == 32
            assert decode_scoped_token(result.setup_token, expected_type="mfa_setup")["sub"] == str(
                result.user_id
            )
            assert result.otpauth_url.startswith("otpauth://totp/")
            assert audit is not None
            assert audit.actor_type == "SYSTEM"
            assert audit.row_hash != "0" * 64

            with pytest.raises(BootstrapError, match="one-time only"):
                bootstrap_first_super_admin(
                    session,
                    "second-owner@example.test",
                    "another-test-password-123",
                )
    finally:
        get_settings.cache_clear()


def test_app_readonly_audit_cannot_read_user_data(db: Connection) -> None:
    add_user(db)
    with db.begin_nested():
        db.execute(text("SET LOCAL ROLE app_readonly_audit"))
        audit_count = db.execute(text("SELECT count(*) FROM audit_logs")).scalar_one()
        assert audit_count == 0

    with pytest.raises(DBAPIError) as error:
        with db.begin_nested():
            db.execute(text("SET LOCAL ROLE app_readonly_audit"))
            db.execute(text("SELECT phone FROM users"))
    assert getattr(error.value.orig, "sqlstate", None) == "42501"