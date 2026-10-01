# DIT — Deterministic Integrity Tower

Deterministic **mediation proxy** for probabilistic generator text. Version `13.1.0` (`src/dit`). Text that cannot satisfy the gate stack does not leave the tower. Text that can leaves normalized, paced, signed, and optionally sealed on a hash chain.

## 1. Pipeline Position & Role

**OUTPUT INTEGRITY** (post-generation, pre-downstream-trust). Complements Conservation Kernel (transformation conservation) and ANVIL (execution lineage). Consumed by [`sentinel_os`](https://github.com/wking53214/sentinel_os) `epistemic/dit_gate.py` (pinned to `26cee7b9`, evaluate() API). **Not** a stage in the observe-perceive orchestrator chain.

```text
generator → oscillation guard → gate stack → normalizer → kinetic governor → HMAC-SHA384 signer → optional HashChainLedger → TowerResult
```

## 2. Full System Scope & Architectural Depth

Assembly of recovered GSA v13 Citadel processor + Deterministic Policy Runtime, with Tier 1 audit findings closed.

| Piece | Status |
|---|---|
| `src/dit/` | Live tower |
| `legacy/gsa_v13_citadel_processor.py` | Recovered engine, defects included; test control only |
| `legacy/dpr_runtime.py` | Recovered; two documented defects; not imported by tower |

Gates (`FULL_STACK` / `GSA_V13_STACK`): Identity, Hedging, Causality, Semantic contamination — independent predicates over **raw generated text**. Retry with instructional delta up to a budget. `run()` returns refusal values; `run_strict()` raises (`TowerCollapse`) for the historical GSA v13 contract.

`StasisSigner.from_env()` HMAC-SHA384. Missing key → `MissingSigningKey`. `HashChainLedger.verify()` recomputes; tamper → `LedgerTampered`. `KineticGovernor` paces release. `OscillationGuard` SHA-256 digests bounded loops.

Lineage: CITADEL regex enforcer → this tower. CITADEL remains an archive.

## 3. What It Does NOT Do / Non-Goals

- Does not decide policy or authorize execution.
- Does not prove the generator's claim is true.
- Regex/heuristic gates ≠ semantic understanding. Hedging/identity/causality patterns can false-positive and false-negative.
- Does not replace Conservation Kernel propositions.

## 4. Brutally Honest Current Status & Gaps

| Gap | Detail |
|---|---|
| Pattern uncalibrated | `GSA_V13_PATTERNS` / default rules — linguistic, not empirically calibrated on a labeled corpus shipped here. |
| Sentinel pin fragility | sentinel_os pins a **branch SHA**. Squash-merge makes it unreachable. |
| HMAC key in env | `KEY_ENV_VAR`; no HSM. |
| Dual ledgers | DIT's HashChainLedger is not sentinel_os Postgres and not observe-perceive ExecutionLedger. |
| Async generator required | Caller supplies `async def generator(prompt) -> str`. |

`python -m dit` demo. `pytest` under `tests/`.

## 5. Core Invariants & Guarantees

Fail-closed: failing gates do not emit unsealed text. Recomputation of ledger hashes. Signing required when signer configured. Refusal is a value (`TowerResult.status`), not a log line.

## 6. Inputs, Outputs & Type Contracts

```python
from dit import DeterministicIntegrityTower, HashChainLedger, StasisSigner, TowerResult
# TowerResult: status, parity, payload, ledger_hash, attempts...
```

## 7. Stack Integration Topology

```text
CITADEL (archive regex)  →  DIT tower
                              ├─ sentinel_os epistemic/dit_gate.py  (LIVE, git pin)
                              └─ observe-perceive                   (not imported)
```

Proprietary. Copyright (c) 2026 William N. King. All rights reserved. See LICENSE. Provenance: `docs/PROVENANCE.md`, `docs/AUDIT_REMEDIATION.md`.
