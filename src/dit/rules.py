"""Linguistic rule sets.

The 2026-07-07 audit recorded "Tight Coupling of Validation Mechanics":
the gates read a module-level ``GSA_REGEX`` dictionary, so changing a rule
meant editing the engine. Rules are data here. A :class:`RuleSet` is built
from a plain mapping of name to pattern, which means a deployment can load
them from YAML, a database, or a per-tenant override without touching the
tower.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Mapping

#: The recovered GSA v13.0 patterns, verbatim. Gate letters are the
#: historical stratum labels from the archive (G1-G6, zero-trust strata).
GSA_V13_PATTERNS: Mapping[str, str] = {
    # G6: Pronominal Purge Array.
    "pronominal_purge": r"\b(i|me|my|mine|myself|we|us|our|ours|ourselves)\b",
    # G3: Syntactic Breach Filter.
    "syntactic_breach": (
        r"\b(may|might|could|seems|generally|potentially|likely|perhaps|maybe)\b"
    ),
    # G6: Conversational Puffery / Corporate Verb Reduction.
    "prohibited_abstract_verbs": (
        r"\b(improve|optimize|enhance|enable|support|strengthen|utilize|leverage)\b"
    ),
    # Causal and Empirical Integrity Verification Gates.
    "causal_link": r"\b(because|due to|driven by|resulting from|caused by)\b",
    "metric_verification": r"\b\d+(\.\d+)?%|\b\d+\b",
    # Epistemic stratum. Recovered from the later DIT gate
    # (sentinel_os/epistemic/dit_gate.py, HyperTestTruthProtocol), which
    # treats an affective marker as a terminal breach rather than a retry.
    "semantic_contamination": r"\b(feel|feels|hope|hopes|believe|believes)\b",
}

#: Patterns whose matching is case-sensitive. ``metric_verification`` is
#: digits only, so the flag is irrelevant to it; every other rule is
#: case-insensitive, as in the recovered engine.
_CASE_SENSITIVE: frozenset[str] = frozenset()


@dataclass(frozen=True)
class RuleSet:
    """A named, compiled, immutable set of linguistic patterns."""

    name: str
    _patterns: Mapping[str, re.Pattern[str]]

    @classmethod
    def from_mapping(
        cls, patterns: Mapping[str, str], *, name: str = "custom"
    ) -> "RuleSet":
        compiled: dict[str, re.Pattern[str]] = {}
        for key, pattern in patterns.items():
            flags = 0 if key in _CASE_SENSITIVE else re.IGNORECASE
            try:
                compiled[key] = re.compile(pattern, flags)
            except re.error as exc:  # pragma: no cover - defensive
                raise ValueError(f"rule {key!r} is not a valid pattern: {exc}") from exc
        return cls(name=name, _patterns=compiled)

    def __getitem__(self, key: str) -> re.Pattern[str]:
        try:
            return self._patterns[key]
        except KeyError:
            raise KeyError(
                f"rule {key!r} is not defined in rule set {self.name!r}; "
                f"defined rules: {sorted(self._patterns)}"
            ) from None

    def __contains__(self, key: object) -> bool:
        return key in self._patterns

    def names(self) -> Iterable[str]:
        return tuple(sorted(self._patterns))

    def requires(self, *keys: str) -> None:
        """Raise if any named rule is absent. Called by gates at build time."""
        missing = [key for key in keys if key not in self._patterns]
        if missing:
            raise KeyError(
                f"rule set {self.name!r} is missing required rules: {missing}"
            )


def default_rules() -> RuleSet:
    """The recovered GSA v13.0 rule set."""
    return RuleSet.from_mapping(GSA_V13_PATTERNS, name="gsa-v13")
