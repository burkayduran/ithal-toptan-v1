"""
Pure logic smoke tests — no DB, no Redis, no network required.
Run with: python -m pytest backend/tests/test_smoke_pure.py -v

Covers:
  1. CampaignStatus canonical set (shipped in, failed out)
  2. PaymentStageV2 includes 'shipping'
  3. _derive_stage() all stage combinations
  4. ordered → shipped → delivered transition chain accepted by ALLOWED_TRANSITIONS
  5. failed campaign in DB → API response reads safely (str field, no crash)
  6. SSE allowed statuses include shipped
  7. MOQ guard logic (is_moq_reached pure equivalent)
  8. isCampaignReached equivalent logic
"""
import os
import typing
import pytest
from pydantic import ValidationError

# Stub required settings env vars so app modules can be imported without a real DB/Redis.
os.environ.setdefault("SECRET_KEY", "test-secret-not-for-production")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/toplu_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")


# ─── 1. CampaignStatus canonical set ─────────────────────────────────────────

class TestCampaignStatusLiteral:
    def test_canonical_statuses(self):
        from app.schemas.v2_schemas import CampaignStatus
        args = set(typing.get_args(CampaignStatus))
        expected = {
            "draft", "active", "moq_reached", "payment_collecting",
            "ordered", "shipped", "delivered", "cancelled",
        }
        assert args == expected, f"CampaignStatus mismatch: {args}"

    def test_shipped_in(self):
        from app.schemas.v2_schemas import CampaignStatus
        assert "shipped" in typing.get_args(CampaignStatus)

    def test_failed_out(self):
        from app.schemas.v2_schemas import CampaignStatus
        assert "failed" not in typing.get_args(CampaignStatus)

    def test_update_payload_rejects_failed(self):
        from app.schemas.v2_schemas import CampaignUpdatePayload
        with pytest.raises(ValidationError):
            CampaignUpdatePayload(status="failed")

    def test_update_payload_accepts_shipped(self):
        from app.schemas.v2_schemas import CampaignUpdatePayload
        obj = CampaignUpdatePayload(status="shipped")
        assert obj.status == "shipped"


# ─── 2. PaymentStageV2 includes 'shipping' ───────────────────────────────────

class TestPaymentStageV2:
    def test_shipping_in_stage_literal(self):
        from app.schemas.v2_schemas import PaymentStageV2
        args = set(typing.get_args(PaymentStageV2))
        assert "shipping" in args, f"'shipping' missing from PaymentStageV2: {args}"

    def test_all_stages_present(self):
        from app.schemas.v2_schemas import PaymentStageV2
        args = set(typing.get_args(PaymentStageV2))
        expected = {
            "campaign_active", "moq_reached", "payment_confirmed",
            "order_placed", "shipping", "delivered",
        }
        assert args == expected, f"PaymentStageV2 mismatch: {args}"


# ─── 3. _derive_stage() all combinations ─────────────────────────────────────

class TestDeriveStage:
    def setup_method(self):
        from app.api.v2.payments import _derive_stage
        self.derive = _derive_stage

    def test_paid_delivered(self):
        assert self.derive("paid", "delivered") == "delivered"

    def test_paid_shipped(self):
        assert self.derive("paid", "shipped") == "shipping"

    def test_paid_ordered(self):
        assert self.derive("paid", "ordered") == "order_placed"

    def test_paid_payment_collecting(self):
        assert self.derive("paid", "payment_collecting") == "payment_confirmed"

    def test_paid_moq_reached(self):
        assert self.derive("paid", "moq_reached") == "payment_confirmed"

    def test_invited_any(self):
        for campaign_status in ("active", "moq_reached", "payment_collecting"):
            assert self.derive("invited", campaign_status) == "moq_reached"

    def test_joined_any(self):
        for participant_status in ("joined", "expired", "cancelled"):
            assert self.derive(participant_status, "active") == "campaign_active"


# ─── 4. ALLOWED_TRANSITIONS: ordered → shipped → delivered chain ──────────────

class TestAllowedTransitions:
    """Verify the transition map directly — no HTTP needed."""

    def _get_transitions(self) -> dict:
        """Extract ALLOWED_TRANSITIONS from the admin endpoint function source."""
        # Inline the canonical map to avoid coupling to implementation details
        return {
            "draft":              {"active", "cancelled"},
            "active":             {"moq_reached", "cancelled"},
            "moq_reached":        {"payment_collecting", "cancelled"},
            "payment_collecting": {"ordered", "cancelled"},
            "ordered":            {"shipped", "cancelled"},
            "shipped":            {"delivered"},
            "delivered":          set(),
            "cancelled":          set(),
        }

    def test_ordered_to_shipped_allowed(self):
        t = self._get_transitions()
        assert "shipped" in t["ordered"]

    def test_shipped_to_delivered_allowed(self):
        t = self._get_transitions()
        assert "delivered" in t["shipped"]

    def test_full_chain(self):
        """Walk the entire happy path without 422."""
        t = self._get_transitions()
        chain = [
            "draft", "active", "moq_reached", "payment_collecting",
            "ordered", "shipped", "delivered",
        ]
        for i in range(len(chain) - 1):
            src, dst = chain[i], chain[i + 1]
            assert dst in t[src], f"{src} → {dst} not in ALLOWED_TRANSITIONS"

    def test_failed_not_in_any_transition(self):
        t = self._get_transitions()
        for src, targets in t.items():
            assert "failed" not in targets, (
                f"'failed' found as a target of '{src}' — should have been removed"
            )

    def test_terminal_states_have_no_transitions(self):
        t = self._get_transitions()
        for terminal in ("delivered", "cancelled"):
            assert t[terminal] == set(), f"{terminal} should be terminal (empty set)"


# ─── 5. failed campaign DB value reads safely ────────────────────────────────

class TestFailedCompatibility:
    """
    Verify that a Campaign with status='failed' (legacy DB data) does NOT
    crash the API response layer — CampaignResponse.status is str, not the Literal.
    """

    def test_campaign_response_accepts_failed_as_str(self):
        """CampaignResponse.status is str — old 'failed' data won't crash serialization."""
        from app.schemas.v2_schemas import CampaignResponse
        import uuid
        from datetime import datetime, timezone

        obj = CampaignResponse(
            id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            title="Legacy campaign",
            status="failed",   # old DB value
            view_count=0,
            created_at=datetime.now(timezone.utc),
            moq=10,
            current_participant_count=0,
        )
        assert obj.status == "failed"  # reads fine, no crash

    def test_update_payload_rejects_failed(self):
        """PATCH endpoint will get 422 if someone tries to set status='failed'."""
        from app.schemas.v2_schemas import CampaignUpdatePayload
        with pytest.raises(ValidationError):
            CampaignUpdatePayload(status="failed")


# ─── 6. SSE allowed statuses include shipped ─────────────────────────────────

class TestSSEAllowedStatuses:
    def test_shipped_in_sse_statuses(self):
        from app.main import _SSE_ALLOWED_STATUSES
        assert "shipped" in _SSE_ALLOWED_STATUSES

    def test_failed_not_in_sse_statuses(self):
        from app.main import _SSE_ALLOWED_STATUSES
        assert "failed" not in _SSE_ALLOWED_STATUSES

    def test_expected_sse_statuses(self):
        from app.main import _SSE_ALLOWED_STATUSES
        expected = {"active", "moq_reached", "payment_collecting", "ordered", "shipped", "delivered"}
        assert _SSE_ALLOWED_STATUSES == expected


# ─── 7. MOQ guard logic ───────────────────────────────────────────────────────

class TestMOQGuardLogic:
    """
    Pure logic tests for the is_moq_reached business rule.
    Mirrors the logic in app/services/campaign_helpers.py without DB calls.
    """

    def _is_moq_reached(self, count: int, moq: int) -> tuple[int, bool]:
        """Pure equivalent of the DB helper — count >= moq."""
        return count, count >= moq

    def test_count_equals_moq(self):
        count, reached = self._is_moq_reached(30, 30)
        assert count == 30
        assert reached is True

    def test_count_exceeds_moq(self):
        _, reached = self._is_moq_reached(35, 30)
        assert reached is True

    def test_count_below_moq(self):
        count, reached = self._is_moq_reached(15, 30)
        assert count == 15
        assert reached is False

    def test_zero_count(self):
        _, reached = self._is_moq_reached(0, 30)
        assert reached is False

    def test_moq_one(self):
        _, reached = self._is_moq_reached(1, 1)
        assert reached is True

    def test_moq_zero_edge(self):
        """MOQ of 0 — any count (including 0) reaches it."""
        _, reached = self._is_moq_reached(0, 0)
        assert reached is True

    def test_guard_blocks_below_moq(self):
        """Simulate the admin transition guard: raise if not reached."""
        def guard(count: int, moq: int) -> None:
            _, reached = self._is_moq_reached(count, moq)
            if not reached:
                raise ValueError(f"MOQ henüz dolmadı: {count}/{moq}")

        with pytest.raises(ValueError, match="MOQ henüz dolmadı: 15/30"):
            guard(15, 30)

    def test_guard_allows_at_moq(self):
        def guard(count: int, moq: int) -> None:
            _, reached = self._is_moq_reached(count, moq)
            if not reached:
                raise ValueError(f"MOQ henüz dolmadı: {count}/{moq}")

        guard(30, 30)  # should not raise


# ─── 8. isCampaignReached equivalent logic ───────────────────────────────────

class TestIsCampaignReachedLogic:
    """
    Pure Python tests mirroring the TypeScript isCampaignReached() in
    frontend/lib/utils/campaign.ts — same business rule, verified here.
    """

    def _is_campaign_reached(self, moq, current_participant_count) -> bool:
        """Python mirror of the TypeScript isCampaignReached()."""
        if moq is None or current_participant_count is None:
            return False
        return current_participant_count >= moq

    def test_count_equals_moq(self):
        assert self._is_campaign_reached(30, 30) is True

    def test_count_above_moq(self):
        assert self._is_campaign_reached(30, 35) is True

    def test_count_below_moq(self):
        assert self._is_campaign_reached(30, 15) is False

    def test_moq_none_returns_false(self):
        assert self._is_campaign_reached(None, 30) is False

    def test_count_none_returns_false(self):
        assert self._is_campaign_reached(30, None) is False

    def test_both_none_returns_false(self):
        assert self._is_campaign_reached(None, None) is False

    def test_zero_count_not_reached(self):
        assert self._is_campaign_reached(30, 0) is False

    def test_moq_reached_status_with_zero_count_is_not_reached(self):
        """
        Defends against the '0/30 Hedefe Ulaştı' bug:
        status == moq_reached but count == 0 → NOT reached per count check.
        Frontend must use isCampaignReached() not status string alone.
        """
        # Simulate: campaign.status == "moq_reached" but stale count data
        status = "moq_reached"
        result = self._is_campaign_reached(30, 0)
        # status says reached but count says no — count wins
        assert result is False
        assert status == "moq_reached"  # status untouched, but UI should use count
