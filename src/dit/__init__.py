"""DIT: the Deterministic Integrity Tower.

A deterministic mediation proxy for probabilistic generators. Text that
cannot satisfy the zero-trust stratum stack does not leave the tower; text
that can leaves signed, paced and, optionally, sealed onto a hash chain.

Reconstructed from the July-August 2026 archive. See docs/PROVENANCE.md for
what was recovered and what was rebuilt, and docs/AUDIT_REMEDIATION.md for
the finding-by-finding accounting against the tower's own Tier 1 audit.

Quick start::

    import asyncio
    from dit import DeterministicIntegrityTower

    async def generator(prompt: str) -> str:
        return "Throughput held because queue depth fell 22%."

    result = asyncio.run(DeterministicIntegrityTower(generator).run("status"))
    print(result.status, result.parity, result.payload)
"""

from .config import FAST, HISTORICAL, LoopScope, TowerConfig
from .evaluate import Evaluation, evaluate, parity_of, run_stack
from .gates import (
    FULL_STACK,
    GSA_V13_STACK,
    CausalityGate,
    Gate,
    HedgingGate,
    IdentityGate,
    SemanticContaminationGate,
    build_stack,
)
from .governor import KineticGovernor
from .injection import build_retry_prompt, neutralize_control_syntax
from .ledger import GENESIS, HashChainLedger, canonical_json
from .normalizer import StructureNormalizer
from .oscillation import OscillationGuard, state_digest
from .results import (
    AttemptRecord,
    DITError,
    GateResult,
    LedgerTampered,
    MissingSigningKey,
    Severity,
    Status,
    TowerCollapse,
    TowerResult,
)
from .rules import GSA_V13_PATTERNS, RuleSet, default_rules
from .signing import KEY_ENV_VAR, StasisSigner
from .telemetry import Telemetry
from .tower import CitadelProcessor, DeterministicIntegrityTower

__version__ = "13.1.0"

__all__ = [
    "AttemptRecord",
    "CausalityGate",
    "CitadelProcessor",
    "DITError",
    "DeterministicIntegrityTower",
    "Evaluation",
    "FAST",
    "FULL_STACK",
    "GENESIS",
    "GSA_V13_PATTERNS",
    "GSA_V13_STACK",
    "Gate",
    "GateResult",
    "HISTORICAL",
    "HashChainLedger",
    "HedgingGate",
    "IdentityGate",
    "KEY_ENV_VAR",
    "KineticGovernor",
    "LedgerTampered",
    "LoopScope",
    "MissingSigningKey",
    "OscillationGuard",
    "RuleSet",
    "SemanticContaminationGate",
    "Severity",
    "StasisSigner",
    "Status",
    "StructureNormalizer",
    "Telemetry",
    "TowerCollapse",
    "TowerConfig",
    "TowerResult",
    "__version__",
    "build_retry_prompt",
    "build_stack",
    "canonical_json",
    "default_rules",
    "evaluate",
    "neutralize_control_syntax",
    "parity_of",
    "run_stack",
    "state_digest",
]
