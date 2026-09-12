"""The DPR runtime as a control.

``legacy/dpr_runtime.py`` is a second recovered artifact from the same
lineage, older than the v13.0 engine by about three weeks. It is preserved as
found and, like ``legacy/gsa_v13_citadel_processor.py``, is imported by this
suite and by nothing else.

These tests pin what the artifact does, including the two places where what it
does is not what it appears to offer. They are documentation of a historical
object, not assertions that its behaviour is correct.
"""

from __future__ import annotations

import hashlib
import hmac

import pytest

import dpr_runtime as dpr
from conftest import run


def _runtime(key: bytes = b"test-signing-key") -> "dpr.DeterministicPolicyRuntime":
    return dpr.DeterministicPolicyRuntime(signing_key=key)


# ---------------------------------------------------------------------------
# Policy evaluation
# ---------------------------------------------------------------------------

def test_empty_input_is_refused():
    result = _runtime().evaluate_policy("   ")
    assert not result.allowed
    assert result.status == "EMPTY_INPUT_VAL"
    assert result.risk_score == 1.0


def test_clean_directive_passes_at_zero_risk():
    result = _runtime().evaluate_policy("EXECUTE PIPELINE_REF_01 :: OPTIMIZE_NODE_CORE")
    assert result.allowed
    assert result.status == "SUCCESS_PASS"
    assert result.risk_score == 0.0


def test_identity_and_courtesy_markers_each_add_their_weight():
    runtime = _runtime()
    identity = runtime.evaluate_policy("I need the report")
    courtesy = runtime.evaluate_policy("please run the report")
    both = runtime.evaluate_policy("please send me the report")

    assert identity.risk_score == pytest.approx(dpr.IDENTITY_WEIGHT)
    assert courtesy.risk_score == pytest.approx(dpr.COURTESY_WEIGHT)
    assert both.risk_score == pytest.approx(dpr.IDENTITY_WEIGHT + dpr.COURTESY_WEIGHT)


def test_long_payloads_add_their_weight():
    long_input = "x" * (dpr.LONG_PAYLOAD_THRESHOLD + 1)
    assert _runtime().evaluate_policy(long_input).risk_score == pytest.approx(
        dpr.LONG_PAYLOAD_WEIGHT
    )


def test_risk_rejection_is_unreachable():
    """The artifact's only live rejection path is the empty-input check.

    The three risk weights sum to 0.45. ``MAX_RISK_THRESHOLD`` is 0.80, so no
    combination of markers can reach it and ``RISK_THRESHOLD_EXCEEDED`` is dead
    code. A reader of ``evaluate_policy`` would reasonably conclude the runtime
    rejects high-risk input; it does not, and never could.
    """
    ceiling = dpr.IDENTITY_WEIGHT + dpr.COURTESY_WEIGHT + dpr.LONG_PAYLOAD_WEIGHT
    assert ceiling < dpr.MAX_RISK_THRESHOLD

    worst_case = "please send me " + ("x" * dpr.LONG_PAYLOAD_THRESHOLD)
    verdict = _runtime().evaluate_policy(worst_case)
    assert verdict.allowed
    assert verdict.status == "SUCCESS_PASS"


# ---------------------------------------------------------------------------
# Attestation
# ---------------------------------------------------------------------------

def test_auth_tag_is_hmac_over_the_forensic_signature():
    key = b"a-specific-key"
    runtime = _runtime(key)
    signature = "deadbeef"
    assert runtime.generate_auth_tag(signature) == hmac.new(
        key, signature.encode(), hashlib.sha256
    ).hexdigest()


def test_auth_tag_depends_on_the_key():
    signature = "deadbeef"
    assert _runtime(b"one").generate_auth_tag(signature) != _runtime(b"two").generate_auth_tag(
        signature
    )


def test_forensic_signature_covers_payload_and_telemetry():
    runtime = _runtime()
    telemetry = dpr.Telemetry(budget_ms=1.0, entropy=1.0, risk_score=0.0)
    other = dpr.Telemetry(budget_ms=1.0, entropy=2.0, risk_score=0.0)

    base = runtime.generate_forensic_signature("payload", telemetry)
    assert runtime.generate_forensic_signature("payload", telemetry) == base
    assert runtime.generate_forensic_signature("different", telemetry) != base
    assert runtime.generate_forensic_signature("payload", other) != base


def test_signing_key_is_injected_not_embedded():
    """The contrast with the v13 engine that succeeded it.

    ``CitadelProcessor`` carried ``GSA_ADAMANTIUM_CORE_STASIS_SIGNATURE_815``
    hardcoded, which ``dit.signing`` now refuses by value. This older artifact
    already took its key as a constructor argument, and its own ``main`` uses
    ``secrets.token_bytes(32)``. The regression happened after it.
    """
    import dit.signing

    source = dpr.DeterministicPolicyRuntime.__init__.__code__.co_consts
    assert not any(
        isinstance(const, bytes) and len(const) > 8 for const in source
    ), "no embedded key material in the constructor"

    runtime = _runtime(dit.signing.COMPROMISED_V13_KEY)
    assert runtime.generate_auth_tag("x")  # it will sign with anything given


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def test_execute_returns_a_full_attestation_envelope():
    result = run(_runtime().execute("EXECUTE PIPELINE_REF_01 :: OPTIMIZE_NODE_CORE"))
    assert result["status"] == 200
    assert result["session_id"].startswith("DPR-")
    assert set(result["telemetry"]) == {"budget_ms", "entropy", "risk_score"}
    assert len(result["forensic_sig"]) == 64
    assert len(result["auth_tag"]) == 64
    assert result["runtime_ms"] > 0


def test_execute_short_circuits_on_refusal():
    result = run(_runtime().execute(""))
    assert result["status"] == 400
    assert result["error"] == "EMPTY_INPUT_VAL"
    assert "forensic_sig" not in result
    assert "auth_tag" not in result


def test_session_ids_are_unique_per_execution():
    runtime = _runtime()
    first = run(runtime.execute("EXECUTE ONE"))
    second = run(runtime.execute("EXECUTE TWO"))
    assert first["session_id"] != second["session_id"]


def test_budget_shrinks_as_the_payload_grows():
    """Longer input raises entropy, which divides the latency budget."""
    runtime = _runtime()
    short = run(runtime.generate_telemetry("short", 0.0))
    long = run(runtime.generate_telemetry("x" * 400, 0.0))
    assert long.entropy > short.entropy
    assert long.budget_ms < short.budget_ms
    assert short.budget_ms <= dpr.DEFAULT_BUDGET_MS
