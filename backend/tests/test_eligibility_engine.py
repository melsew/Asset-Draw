"""Unit tests for the Eligibility & Entry Engine (entries/eligibility.py).

These tests use Python-level mocks — no live database required.
Each test corresponds to one of the six mandatory eligibility questions.

To run:
    cd backend && pytest tests/test_eligibility_engine.py -v
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.entries.eligibility import (
    EligibilityCode,
    EligibilityResult,
    check_eligibility,
)


# ── Factories ─────────────────────────────────────────────────────────────────

NOW = datetime.now(timezone.utc)


def _user(status: str = "ACTIVE", phone_verified: bool = True) -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.status = status
    u.phone_verified_at = (NOW - timedelta(hours=1)) if phone_verified else None
    return u


def _campaign(
    *,
    status: str = "ACTIVE",
    entry_mode: str = "FREE",
    max_entries: int = 100,
    per_user_limit: int = 1,
    end_at_offset: timedelta = timedelta(days=1),
) -> MagicMock:
    c = MagicMock()
    c.id = uuid.uuid4()
    c.status = status
    c.entry_mode = entry_mode
    c.max_entries = max_entries
    c.per_user_limit = per_user_limit
    c.end_at = NOW + end_at_offset
    c.entry_price = Decimal("50.00") if entry_mode in ("PURCHASE", "PAID_ENTRY") else None
    return c


def _session(
    campaign: MagicMock | None = None,
    existing_entries: int = 0,
    active_entries: int = 0,
    approval: MagicMock | None = None,
    payment: MagicMock | None = None,
) -> MagicMock:
    """Build a minimal mock Session that answers the queries the engine fires."""
    session = MagicMock()

    def scalar_side_effect(stmt):
        # Identify the query by inspecting the compiled string (duck-typing approach)
        stmt_str = str(stmt)
        if "campaigns" in stmt_str:
            return campaign
        if "entry_mode_approvals" in stmt_str:
            return approval
        if "payments" in stmt_str:
            return payment
        # func.count() queries — return the right integer
        if "count" in stmt_str:
            if "user_id" in stmt_str:
                return existing_entries
            return active_entries
        return None

    session.scalar.side_effect = scalar_side_effect
    return session


# ── Q1: Is the user eligible? ─────────────────────────────────────────────────

class TestQ1UserEligible:
    def test_active_user_passes(self) -> None:
        campaign = _campaign()
        session = _session(campaign=campaign)
        result = check_eligibility(session, _user(status="ACTIVE"), campaign.id)
        assert result.eligible is True
        assert result.code == EligibilityCode.OK

    def test_suspended_user_is_denied(self) -> None:
        session = _session(campaign=_campaign())
        result = check_eligibility(session, _user(status="SUSPENDED"), uuid.uuid4())
        assert result.eligible is False
        assert result.code == EligibilityCode.USER_NOT_ACTIVE

    def test_disabled_user_is_denied(self) -> None:
        session = _session(campaign=_campaign())
        result = check_eligibility(session, _user(status="DISABLED"), uuid.uuid4())
        assert result.eligible is False
        assert result.code == EligibilityCode.USER_NOT_ACTIVE


# ── Q2: Is the campaign active? ───────────────────────────────────────────────

class TestQ2CampaignActive:
    def test_missing_campaign_returns_not_found(self) -> None:
        session = _session(campaign=None)
        result = check_eligibility(session, _user(), uuid.uuid4())
        assert result.eligible is False
        assert result.code == EligibilityCode.CAMPAIGN_NOT_FOUND

    @pytest.mark.parametrize("bad_status", [
        "DRAFT", "SUBMITTED", "UNDER_REVIEW", "APPROVED", "ASSET_VERIFIED",
        "SCHEDULED", "SUSPENDED", "ENTRY_CLOSED", "POOL_LOCKED",
        "DRAWING", "DRAW_COMPLETED", "WINNER_VERIFIED", "PRIZE_DELIVERED",
        "COMPLETED", "CANCELLED", "REJECTED",
    ])
    def test_non_active_campaign_is_denied(self, bad_status: str) -> None:
        campaign = _campaign(status=bad_status)
        session = _session(campaign=campaign)
        result = check_eligibility(session, _user(), campaign.id)
        assert result.eligible is False
        assert result.code == EligibilityCode.CAMPAIGN_NOT_ACTIVE

    def test_active_campaign_passes(self) -> None:
        campaign = _campaign(status="ACTIVE")
        session = _session(campaign=campaign)
        result = check_eligibility(session, _user(), campaign.id)
        assert result.eligible is True


# ── Q3: Is participation still open? ─────────────────────────────────────────

class TestQ3ParticipationOpen:
    def test_expired_campaign_is_denied(self) -> None:
        campaign = _campaign(end_at_offset=timedelta(hours=-1))
        session = _session(campaign=campaign)
        result = check_eligibility(session, _user(), campaign.id)
        assert result.eligible is False
        assert result.code == EligibilityCode.PARTICIPATION_CLOSED

    def test_ending_in_future_passes(self) -> None:
        campaign = _campaign(end_at_offset=timedelta(seconds=30))
        session = _session(campaign=campaign)
        result = check_eligibility(session, _user(), campaign.id)
        assert result.eligible is True

    def test_exactly_at_end_at_is_closed(self) -> None:
        """end_at IS the deadline: campaign.end_at < now() → closed."""
        campaign = _campaign(end_at_offset=timedelta(seconds=-1))
        session = _session(campaign=campaign)
        result = check_eligibility(session, _user(), campaign.id)
        assert result.eligible is False
        assert result.code == EligibilityCode.PARTICIPATION_CLOSED


# ── Q4: Has the user already participated? ────────────────────────────────────

class TestQ4AlreadyEntered:
    def test_no_existing_entry_passes(self) -> None:
        campaign = _campaign(per_user_limit=1)
        session = _session(campaign=campaign, existing_entries=0)
        result = check_eligibility(session, _user(), campaign.id)
        assert result.eligible is True

    def test_at_limit_is_denied(self) -> None:
        campaign = _campaign(per_user_limit=1)
        session = _session(campaign=campaign, existing_entries=1)
        result = check_eligibility(session, _user(), campaign.id)
        assert result.eligible is False
        assert result.code == EligibilityCode.ALREADY_ENTERED

    def test_below_multi_limit_passes(self) -> None:
        campaign = _campaign(per_user_limit=3)
        session = _session(campaign=campaign, existing_entries=2)
        result = check_eligibility(session, _user(), campaign.id)
        assert result.eligible is True

    def test_at_multi_limit_is_denied(self) -> None:
        campaign = _campaign(per_user_limit=3)
        session = _session(campaign=campaign, existing_entries=3)
        result = check_eligibility(session, _user(), campaign.id)
        assert result.eligible is False
        assert result.code == EligibilityCode.ALREADY_ENTERED


# ── Q5: Is campaign capacity available? ───────────────────────────────────────

class TestQ5CapacityAvailable:
    def test_under_capacity_passes(self) -> None:
        campaign = _campaign(max_entries=10)
        session = _session(campaign=campaign, existing_entries=0, active_entries=9)
        result = check_eligibility(session, _user(), campaign.id)
        assert result.eligible is True

    def test_at_capacity_is_denied(self) -> None:
        campaign = _campaign(max_entries=10)
        session = _session(campaign=campaign, existing_entries=0, active_entries=10)
        result = check_eligibility(session, _user(), campaign.id)
        assert result.eligible is False
        assert result.code == EligibilityCode.CAMPAIGN_FULL

    def test_over_capacity_is_denied(self) -> None:
        campaign = _campaign(max_entries=5)
        session = _session(campaign=campaign, existing_entries=0, active_entries=99)
        result = check_eligibility(session, _user(), campaign.id)
        assert result.eligible is False
        assert result.code == EligibilityCode.CAMPAIGN_FULL


# ── Q6: Has the qualifying action been verified? ──────────────────────────────

class TestQ6QualifyingAction:
    def test_free_mode_requires_no_action(self) -> None:
        campaign = _campaign(entry_mode="FREE")
        session = _session(campaign=campaign)
        result = check_eligibility(session, _user(), campaign.id)
        assert result.eligible is True

    def test_promotional_mode_requires_no_action(self) -> None:
        campaign = _campaign(entry_mode="PROMOTIONAL")
        session = _session(campaign=campaign)
        result = check_eligibility(session, _user(), campaign.id)
        assert result.eligible is True

    def test_purchase_mode_blocked_without_d01_approval(self) -> None:
        campaign = _campaign(entry_mode="PURCHASE")
        session = _session(campaign=campaign, approval=None)
        result = check_eligibility(session, _user(), campaign.id, payment_id=uuid.uuid4())
        assert result.eligible is False
        assert result.code == EligibilityCode.D01_GATE_PAID_ENTRY

    def test_paid_entry_blocked_without_d01_approval(self) -> None:
        campaign = _campaign(entry_mode="PAID_ENTRY")
        session = _session(campaign=campaign, approval=None)
        result = check_eligibility(session, _user(), campaign.id, payment_id=uuid.uuid4())
        assert result.eligible is False
        assert result.code == EligibilityCode.D01_GATE_PAID_ENTRY

    def test_purchase_mode_with_d01_but_no_payment_id(self) -> None:
        campaign = _campaign(entry_mode="PURCHASE")
        approval = MagicMock()
        session = _session(campaign=campaign, approval=approval)
        result = check_eligibility(session, _user(), campaign.id, payment_id=None)
        assert result.eligible is False
        assert result.code == EligibilityCode.PAYMENT_REQUIRED

    def test_purchase_mode_with_d01_and_succeeded_payment_passes(self) -> None:
        campaign = _campaign(entry_mode="PURCHASE")
        approval = MagicMock()
        payment = MagicMock()
        payment.status = "SUCCEEDED"
        session = _session(campaign=campaign, approval=approval, payment=payment)
        result = check_eligibility(session, _user(), campaign.id, payment_id=uuid.uuid4())
        assert result.eligible is True

    def test_purchase_mode_with_unconfirmed_payment_is_denied(self) -> None:
        campaign = _campaign(entry_mode="PURCHASE")
        approval = MagicMock()
        for bad_status in ("INITIATED", "PENDING", "FAILED", "EXPIRED"):
            payment = MagicMock()
            payment.status = bad_status
            session = _session(campaign=campaign, approval=approval, payment=payment)
            result = check_eligibility(session, _user(), campaign.id, payment_id=uuid.uuid4())
            assert result.eligible is False, f"Expected DENIED for payment status {bad_status}"
            assert result.code == EligibilityCode.PAYMENT_NOT_CONFIRMED

    def test_referral_mode_without_code_is_denied(self) -> None:
        campaign = _campaign(entry_mode="REFERRAL")
        session = _session(campaign=campaign)
        result = check_eligibility(session, _user(), campaign.id, referral_code=None)
        assert result.eligible is False
        assert result.code == EligibilityCode.REFERRAL_NOT_VERIFIED


# ── EligibilityResult helpers ─────────────────────────────────────────────────

class TestEligibilityResult:
    def test_allow_returns_ok(self) -> None:
        r = EligibilityResult.allow()
        assert r.eligible is True
        assert r.code == EligibilityCode.OK

    def test_deny_returns_false(self) -> None:
        r = EligibilityResult.deny(EligibilityCode.CAMPAIGN_FULL)
        assert r.eligible is False
        assert r.code == EligibilityCode.CAMPAIGN_FULL
        assert isinstance(r.message, str) and len(r.message) > 0

    def test_all_codes_have_messages(self) -> None:
        """Every EligibilityCode must map to a non-empty message."""
        from app.entries.eligibility import _MESSAGES
        for code in EligibilityCode:
            assert code in _MESSAGES, f"Missing message for {code}"
            assert _MESSAGES[code], f"Empty message for {code}"

    def test_deny_preserves_detail(self) -> None:
        detail = {"campaign_id": "abc", "max_entries": 10}
        r = EligibilityResult.deny(EligibilityCode.CAMPAIGN_FULL, detail=detail)
        assert r.detail == detail


# ── Check ordering: earlier failures short-circuit later checks ───────────────

class TestCheckOrdering:
    def test_suspended_user_short_circuits_before_campaign_lookup(self) -> None:
        """A SUSPENDED user must be rejected before we even look up the campaign."""
        session = MagicMock()
        session.scalar.return_value = None  # would return no campaign
        result = check_eligibility(session, _user(status="SUSPENDED"), uuid.uuid4())
        # scalar should NOT have been called (no campaign lookup needed)
        session.scalar.assert_not_called()
        assert result.code == EligibilityCode.USER_NOT_ACTIVE

    def test_campaign_not_found_short_circuits_before_capacity_check(self) -> None:
        session = _session(campaign=None)
        result = check_eligibility(session, _user(), uuid.uuid4())
        assert result.code == EligibilityCode.CAMPAIGN_NOT_FOUND
        # scalar was called once (campaign lookup), not more
        assert session.scalar.call_count == 1

    def test_inactive_campaign_short_circuits_before_user_limit_check(self) -> None:
        """An inactive campaign should block before we count user entries."""
        campaign = _campaign(status="COMPLETED")
        session = _session(campaign=campaign)
        result = check_eligibility(session, _user(), campaign.id)
        assert result.code == EligibilityCode.CAMPAIGN_NOT_ACTIVE
        # scalar called once (campaign), not the entry count queries
        assert session.scalar.call_count == 1
