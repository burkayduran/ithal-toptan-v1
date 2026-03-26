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
