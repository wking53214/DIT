"""The Deterministic Integrity Tower.

A mediation proxy that sits between a caller and a probabilistic generator.
Text leaves the tower only if it satisfies every gate in the stratum stack;
text that fails is re-requested with an instructional delta naming what was
wrong, up to a bounded retry budget. What leaves is signed and, when a
ledger is attached, sealed onto a hash chain.

Pipeline, in order::

    prompt
      -> generator                     (caller-supplied, awaited)
      -> oscillation guard             SHA-256 digest, bounded + scoped
      -> gate stack                    raw text, terminal gates first
      -> structure normalizer          post-pass, gate-safe by construction
      -> kinetic governor              paced release
      -> stasis signer                 HMAC-SHA384
      -> hash-chain ledger             optional, tamper-evident
      -> TowerResult

Every step is a value returning to the caller, including refusal.
:meth:`DeterministicIntegrityTower.run` does not raise for an exhausted
retry budget; :meth:`run_strict` does, for callers who want the historical
GSA v13.0 contract.
"""

from __future__ import annotations

import time
from dataclasses import replace
from typing import Awaitable, Callable, Sequence

from .config import HISTORICAL, LoopScope, TowerConfig
from .evaluate import parity_of, run_stack
from .gates import GSA_V13_STACK, Gate, build_stack
from .governor import KineticGovernor
from .injection import build_retry_prompt
from .ledger import HashChainLedger
from .normalizer import StructureNormalizer
from .oscillation import OscillationGuard, state_digest
from .results import (
    AttemptRecord,
    GateResult,
    Severity,
    Status,
    TowerCollapse,
    TowerResult,
)
from .rules import RuleSet, default_rules
from .signing import StasisSigner
from .telemetry import Telemetry

Generator = Callable[[str], Awaitable[str]]

_LOOP_FAILURE = "Generative loop iteration pattern triggered."


class DeterministicIntegrityTower:
    """The core engine.

    Args:
        generator: an awaitable taking a prompt and returning raw text.
        config: the operating envelope. Defaults to the historical profile.
        rules: the linguistic rule set. Defaults to the GSA v13.0 patterns.
        gates: an explicit gate stack. Defaults to the three retryable
            strata; pass :data:`dit.gates.FULL_STACK` to add the epistemic
            terminal gate.
        signer: stasis signer. Defaults to a process-local ephemeral key,
            so an unconfigured tower still runs but cannot mint signatures
            that outlive it. Pass ``StasisSigner.from_env()`` in production.
        ledger: attach one to seal each transaction onto a hash chain.
    """

    def __init__(
        self,
        generator: Generator,
        *,
        config: TowerConfig | None = None,
        rules: RuleSet | None = None,
        gates: Sequence[Gate] | None = None,
        signer: StasisSigner | None = None,
        ledger: HashChainLedger | None = None,
        telemetry: Telemetry | None = None,
    ) -> None:
        self._generator = generator
        self.config = config or HISTORICAL
        self.rules = rules or default_rules()
        self.gates: tuple[Gate, ...] = (
            tuple(gates) if gates is not None else build_stack(self.rules, GSA_V13_STACK)
        )
        self.normalizer = StructureNormalizer(self.rules)
        self.governor = KineticGovernor(self.config)
        self.signer = signer or StasisSigner.generate()
        self.ledger = ledger
        self.telemetry = telemetry or Telemetry()
        # Instance-scoped guard, used only when configured. A run-scoped
        # tower builds a fresh guard per transaction instead.
        self._instance_guard = OscillationGuard(self.config)

    # -- internals ----------------------------------------------------

    def _guard(self) -> OscillationGuard:
        if self.config.loop_scope is LoopScope.INSTANCE:
            return self._instance_guard
        return OscillationGuard(self.config)

    def _evaluate(self, text: str) -> tuple[GateResult, ...]:
        """Run every gate. Shared with dit.evaluate so the two cannot drift."""
        return run_stack(text, self.gates)

    def _seal(self, result: TowerResult, prompt_digest: str) -> str | None:
        if self.ledger is None:
            return None
        return self.ledger.append(
            {
                "cycle": "DIT_TRANSACTION",
                "status": result.status.value,
                "parity": result.parity,
                "attempts": result.attempts,
                "prompt_digest": prompt_digest,
                "payload_digest": (
                    state_digest(result.payload) if result.payload is not None else None
                ),
                "checksum": result.checksum,
                "failures": list(result.failures),
            }
        )

    # -- public API ---------------------------------------------------

    async def run(self, prompt: str) -> TowerResult:
        """Drive one transaction to a verdict. Never raises on refusal."""
        guard = self._guard()
        started = time.monotonic()
        prompt_digest = state_digest(prompt)
        accumulated: list[str] = []
        history: list[AttemptRecord] = []
        working_prompt = prompt
        last_results: tuple[GateResult, ...] = ()

        self.telemetry.emit(
            "transaction.start",
            prompt_digest=prompt_digest,
            max_attempts=self.config.max_attempts,
            gates=[gate.name for gate in self.gates],
        )

        for attempt in range(1, self.config.max_attempts + 1):
            raw_output = await self._generator(working_prompt)

            digest = state_digest(raw_output)
            looped = guard.seen(digest)
            guard.remember(digest)

            # Gates see the payload as generated; normalization is a
            # post-pass. See the ordering invariant in dit.gates.
            results = self._evaluate(raw_output)
            last_results = results

            failures = tuple(
                result.reason for result in results if not result.passed
            )
            if looped:
                failures = failures + (_LOOP_FAILURE,)

            history.append(
                AttemptRecord(
                    attempt=attempt,
                    digest=digest,
                    looped=looped,
                    gate_results=results,
                    failures=failures,
                )
            )

            terminal = next(
                (
                    result
                    for result in results
                    if not result.passed and result.severity is Severity.TERMINAL
                ),
                None,
            )
            if terminal is not None:
                outcome = TowerResult(
                    status=Status.TERMINAL_BREACH,
                    parity=parity_of(results),
                    attempts=attempt,
                    latency_ms=round((time.monotonic() - started) * 1000.0, 2),
                    payload=None,
                    failures=failures,
                    history=tuple(history),
                    metadata={"terminal_gate": terminal.gate},
                )
                ledger_hash = self._seal(outcome, prompt_digest)
                self.telemetry.emit(
                    "transaction.terminal",
                    gate=terminal.gate,
                    attempt=attempt,
                    reason=terminal.reason,
                )
                return replace(outcome, ledger_hash=ledger_hash)

            if not failures:
                payload = self.normalizer.normalize(raw_output)
                waited = await self.governor.pace(payload)
                checksum = self.signer.sign(payload)
                outcome = TowerResult(
                    status=Status.PASS,
                    parity=1.0000,
                    attempts=attempt,
                    latency_ms=round((time.monotonic() - started) * 1000.0, 2),
                    payload=payload,
                    checksum=checksum,
                    history=tuple(history),
                    metadata={
                        "paced_seconds": round(waited, 4),
                        "normalized": payload != raw_output,
                        "ephemeral_signature": self.signer.ephemeral,
                    },
                )
                ledger_hash = self._seal(outcome, prompt_digest)
                self.telemetry.emit(
                    "transaction.pass", attempt=attempt, checksum=checksum
                )
                return replace(outcome, ledger_hash=ledger_hash)

            # Accumulate across attempts rather than rebuilding from the
            # base prompt: the audit's "Fix Prompt Concatenation Logic".
            for reason in failures:
                if reason not in accumulated:
                    accumulated.append(reason)
            working_prompt = build_retry_prompt(
                prompt,
                tuple(accumulated),
                max_delta_chars=self.config.max_delta_chars,
                max_prompt_chars=self.config.max_prompt_chars,
            )
            self.telemetry.emit(
                "transaction.retry", attempt=attempt, failures=list(failures)
            )

        outcome = TowerResult(
            status=Status.EXHAUSTED,
            parity=parity_of(last_results),
            attempts=self.config.max_attempts,
            latency_ms=round((time.monotonic() - started) * 1000.0, 2),
            payload=None,
            failures=tuple(accumulated),
            history=tuple(history),
        )
        ledger_hash = self._seal(outcome, prompt_digest)
        self.telemetry.emit(
            "transaction.exhausted",
            attempts=self.config.max_attempts,
            failures=list(accumulated),
        )
        return replace(outcome, ledger_hash=ledger_hash)

    async def run_strict(self, prompt: str) -> TowerResult:
        """As :meth:`run`, but raise :class:`TowerCollapse` on refusal.

        The GSA v13.0 contract, with evidence attached to the exception.
        """
        result = await self.run(prompt)
        if not result.ok:
            raise TowerCollapse(result)
        return result


#: Lineage alias. The engine was named for the Citadel architecture it grew
#: out of; the class was ``CitadelProcessor`` in GSA v13.0.
CitadelProcessor = DeterministicIntegrityTower
