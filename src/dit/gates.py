"""The zero-trust gate stratum.

Each gate is an independent, side-effect-free predicate over candidate text.
Gates are constructed against a :class:`~dit.rules.RuleSet`, so a deployment
composes its own stack rather than editing the engine.

Ordering invariant
------------------
Gates run against the payload **as generated**, before
:class:`~dit.normalizer.StructureNormalizer` rewrites it. The audit's
"Destructive Normalization Ordering" finding described the inverse: the
recovered engine normalized first, so "optimized due to high load" became
"use due to high load" and the causality gate then evaluated a corrupted
sentence. Normalization is a post-pass transformation here and, by
construction, touches only the abstract-verb vocabulary, which no gate
inspects.
"""

from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

from .results import GateResult, Severity
from .rules import RuleSet


@runtime_checkable
class Gate(Protocol):
    """The contract every stratum filter satisfies."""

    name: str

    def check(self, text: str) -> GateResult: ...


class _RuleGate:
    """Shared machinery for the rule-backed gates."""

    name = "rule"
    severity = Severity.RETRYABLE
    _required: tuple[str, ...] = ()

    def __init__(self, rules: RuleSet) -> None:
        rules.requires(*self._required)
        self._rules = rules


class IdentityGate(_RuleGate):
    """G6: structural erasure of first-person perspective.

    An artefact that speaks as "I" or "we" carries an implied author, and
    the tower's whole purpose is output that stands on evidence rather than
    on a speaker.
    """

    name = "identity"
    _required = ("pronominal_purge",)

    def check(self, text: str) -> GateResult:
        match = self._rules["pronominal_purge"].search(text)
        if match is None:
            return GateResult(self.name, True)
        return GateResult(
            self.name,
            False,
            Severity.RETRYABLE,
            f"First-person identifier usage detected: {match.group(0)!r}.",
        )


class HedgingGate(_RuleGate):
    """G3: eradication of epistemic hedging.

    "may", "might", "seems" mark a claim the generator declined to commit
    to. The tower rejects the render rather than pass uncertainty downstream
    disguised as a finding.
    """

    name = "hedging"
    _required = ("syntactic_breach",)

    def check(self, text: str) -> GateResult:
        match = self._rules["syntactic_breach"].search(text)
        if match is None:
            return GateResult(self.name, True)
        return GateResult(
            self.name,
            False,
            Severity.RETRYABLE,
            "Subjective hedging / unverified statements detected: "
            f"{match.group(0)!r}.",
        )


class CausalityGate(_RuleGate):
    """Empirical anchoring: a causal connective or a measured quantity.

    This is the one gate that requires a positive signal rather than the
    absence of one. A declarative sentence that cites neither cause nor
    number is an assertion with nothing behind it.
    """

    name = "causality"
    _required = ("causal_link", "metric_verification")

    def check(self, text: str) -> GateResult:
        has_causality = bool(self._rules["causal_link"].search(text))
        has_metrics = bool(self._rules["metric_verification"].search(text))
        if has_causality or has_metrics:
            return GateResult(self.name, True)
        return GateResult(
            self.name,
            False,
            Severity.RETRYABLE,
            "Output missing objective metrics or explicit causal links.",
        )


class SemanticContaminationGate(_RuleGate):
    """Epistemic stratum: an affective marker is a terminal breach.

    Recovered from the later DIT gate (``HyperTestTruthProtocol``), whose
    bedrock axioms are "Logic > Meaning" and "Truth > Optics". Unlike the
    three strata above, this failure is not retryable: a generator that
    reports what it feels or believes has left the evidentiary frame, and
    an instructional delta asking it to try again does not restore the
    frame, it just asks for the same claim in flatter prose.
    """

    name = "semantic_contamination"
    severity = Severity.TERMINAL
    _required = ("semantic_contamination",)

    def check(self, text: str) -> GateResult:
        match = self._rules["semantic_contamination"].search(text)
        if match is None:
            return GateResult(self.name, True)
        return GateResult(
            self.name,
            False,
            Severity.TERMINAL,
            f"TERMINAL_LOGIC_BREACH: EMOTIONAL_LEAK ({match.group(0)!r}).",
        )


#: The three retryable strata of the recovered GSA v13.0 engine.
GSA_V13_STACK: tuple[type[_RuleGate], ...] = (
    IdentityGate,
    HedgingGate,
    CausalityGate,
)

#: v13 plus the epistemic terminal gate recovered from the later DIT.
FULL_STACK: tuple[type[_RuleGate], ...] = GSA_V13_STACK + (SemanticContaminationGate,)


def build_stack(
    rules: RuleSet, gates: Sequence[type[_RuleGate]] = GSA_V13_STACK
) -> tuple[Gate, ...]:
    """Instantiate a gate stack against one rule set."""
    return tuple(gate(rules) for gate in gates)
