"""Structural normalization.

Reduces the abstract commercial verb vocabulary ("optimize", "leverage")
to one primitive. This runs *after* the gate stack, not before it: see the
ordering invariant in :mod:`dit.gates`.
"""

from __future__ import annotations

from .rules import RuleSet


class StructureNormalizer:
    """G2/G3 attachment: collapses corporate filler to a single primitive."""

    name = "structure"

    def __init__(self, rules: RuleSet, *, replacement: str = "use") -> None:
        rules.requires("prohibited_abstract_verbs")
        self._rules = rules
        self._replacement = replacement

    def normalize(self, text: str) -> str:
        return self._rules["prohibited_abstract_verbs"].sub(self._replacement, text)

    def would_change(self, text: str) -> bool:
        return bool(self._rules["prohibited_abstract_verbs"].search(text))
