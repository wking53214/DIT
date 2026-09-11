import pytest

from conftest import COMPLIANT, constant, run, scripted
from dit import (
    FAST,
    FULL_STACK,
    DeterministicIntegrityTower,
    HashChainLedger,
    LoopScope,
    StasisSigner,
    Status,
    TowerCollapse,
    build_stack,
    default_rules,
    state_digest,
)


def tower(generator, **kwargs):
    kwargs.setdefault("config", FAST)
    return DeterministicIntegrityTower(generator, **kwargs)


def test_compliant_payload_passes_on_the_first_attempt():
    result = run(tower(constant(COMPLIANT)).run("status"))
    assert result.status is Status.PASS
    assert result.ok
    assert result.parity == 1.0
    assert result.attempts == 1
    assert result.payload == COMPLIANT


def test_released_payload_carries_a_verifiable_signature():
    signer = StasisSigner(b"0123456789abcdef0123456789abcdef")
    result = run(tower(constant(COMPLIANT), signer=signer).run("status"))
    assert signer.verify(result.payload, result.checksum)


def test_drift_is_recovered_after_the_delta_lands():
    """The case the GSA v13.0 engine could not clear.

    Its retry prompt discarded accumulated context, so the generator was
    asked the same question each time.
    """
    generator = scripted("I think we can optimize the pipeline.", COMPLIANT)
    result = run(tower(generator).run("status"))
    assert result.status is Status.PASS
    assert result.attempts == 2
    assert "INSTRUCTIONAL_DELTA" in generator.prompts[1]


def test_retry_prompt_names_every_failed_gate():
    generator = scripted("I think this may work.", COMPLIANT)
    run(tower(generator).run("status"))
    delta = generator.prompts[1]
    assert "First-person" in delta
    assert "hedging" in delta


def test_exhaustion_is_a_value_not_an_exception():
    """The audit's 'Brittle Exception-Driven Flow Control'."""
    result = run(tower(constant("I think this may work.")).run("status"))
    assert result.status is Status.EXHAUSTED
    assert not result.ok
    assert result.payload is None
    assert result.attempts == FAST.max_attempts
    assert result.failures


def test_exhausted_parity_reports_how_close_the_render_came():
    result = run(tower(constant("Throughput rose sharply.")).run("status"))
    # identity and hedging pass, causality does not: 2 of 3.
    assert result.parity == pytest.approx(2 / 3, abs=1e-4)


def test_run_strict_preserves_the_historical_contract():
    with pytest.raises(TowerCollapse) as excinfo:
        run(tower(constant("I think this may work.")).run_strict("status"))
    assert "1.0000 Parity unachievable" in str(excinfo.value)
    assert excinfo.value.result.status is Status.EXHAUSTED


def test_run_strict_returns_the_result_on_success():
    result = run(tower(constant(COMPLIANT)).run_strict("status"))
    assert result.ok


def test_history_records_every_attempt():
    generator = scripted("I think this may work.", COMPLIANT)
    result = run(tower(generator).run("status"))
    assert [record.attempt for record in result.history] == [1, 2]
    assert result.history[0].failures
    assert result.history[1].passed


def test_repeated_output_is_classified_as_oscillation():
    result = run(tower(constant("Throughput rose sharply.")).run("status"))
    assert any("loop" in reason.lower() for reason in result.failures)


def test_loop_memory_does_not_leak_between_transactions():
    """The audit's 'State Leakage across Transactions'.

    The same compliant payload in two separate transactions is not a loop.
    """
    engine = tower(constant(COMPLIANT))
    first = run(engine.run("status"))
    second = run(engine.run("status"))
    assert first.status is second.status is Status.PASS


def test_instance_scope_is_available_when_asked_for():
    engine = tower(constant(COMPLIANT), config=FAST.with_(loop_scope=LoopScope.INSTANCE))
    assert run(engine.run("status")).status is Status.PASS
    assert run(engine.run("status")).status is Status.EXHAUSTED


def test_normalization_runs_after_the_gates():
    """The audit's 'Destructive Normalization Ordering'.

    The gates judge the payload as generated; the abstract-verb rewrite
    happens on release. test_audit_findings.py pins the failure mode this
    ordering removes.
    """
    payload = "Teams optimize throughput because load rose 12%."
    result = run(tower(constant(payload)).run("status"))
    assert result.status is Status.PASS
    assert result.payload == "Teams use throughput because load rose 12%."
    assert result.metadata["normalized"] is True


def test_terminal_breach_refuses_without_spending_retries():
    engine = tower(
        constant("The team believes 4 nodes failed."),
        gates=build_stack(default_rules(), FULL_STACK),
    )
    result = run(engine.run("status"))
    assert result.status is Status.TERMINAL_BREACH
    assert result.attempts == 1
    assert result.metadata["terminal_gate"] == "semantic_contamination"
    assert result.payload is None


def test_ledger_seals_every_transaction():
    ledger = HashChainLedger()
    engine = tower(constant(COMPLIANT), ledger=ledger)
    result = run(engine.run("status"))
    assert result.ledger_hash == ledger.head
    assert len(ledger) == 1
    assert ledger.verify()


def test_ledger_records_refusals_too():
    ledger = HashChainLedger()
    engine = tower(constant("I think this may work."), ledger=ledger)
    result = run(engine.run("status"))
    assert ledger.entries()[0]["status"] == Status.EXHAUSTED.value
    assert result.ledger_hash is not None


def test_ledger_stores_digests_not_payloads():
    """A tower that governs sensitive text must not leak it into the audit
    trail. The chain proves what was released without restating it."""
    ledger = HashChainLedger()
    run(tower(constant(COMPLIANT), ledger=ledger).run("secret prompt"))
    entry = ledger.entries()[0]
    assert entry["payload_digest"] == state_digest(COMPLIANT)
    assert COMPLIANT not in str(entry)
    assert "secret prompt" not in str(entry)


def test_telemetry_reports_the_transaction_arc():
    engine = tower(scripted("I think this may work.", COMPLIANT))
    run(engine.run("status"))
    events = [event["event"] for event in engine.telemetry.events]
    assert events == [
        "transaction.start",
        "transaction.retry",
        "transaction.pass",
    ]


def test_retry_budget_is_honoured_exactly():
    generator = constant("I think this may work.")
    engine = tower(generator, config=FAST.with_(max_attempts=2))
    result = run(engine.run("status"))
    assert result.attempts == 2
    assert len(generator.prompts) == 2


def test_citadel_processor_alias_is_the_tower():
    from dit import CitadelProcessor

    assert CitadelProcessor is DeterministicIntegrityTower


def test_generator_receives_the_original_prompt_first():
    generator = constant(COMPLIANT)
    run(tower(generator).run("the original prompt"))
    assert generator.prompts[0] == "the original prompt"
