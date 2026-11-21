# DIT, Deterministic Integrity Tower

Deterministic **mediation proxy** for probabilistic generator text. Version `13.1.0` (`src/dit`). Text that cannot satisfy the gate stack does not leave the tower. Text that can leaves normalized, paced, signed, and optionally sealed on a hash chain.

## Role Within ≡TACK

- **What it is.** An output integrity gate for generator text: gates, normalizer, pacing, HMAC signing and an optional hash chain.
- **Authority matrix.** Evaluation (heuristic gates), evidence generation (HMAC signature, optional hash chain). It does not define policy, authorize, or authenticate a caller. The HMAC key is one symmetric key, so a signature shows integrity under that key, not who signed.
- **Does not own.** Policy, authorization, truth of the generator's claims, or transformation conservation (Conservation Kernel).
- **Depends on.** See `pyproject.toml` (not re-listed here). The README states a CNS connection is optional (section 8).
- **Depended on by.** sentinel_os `epistemic/dit_gate.py` (checked 2026-11-18 at sentinel_os `55aa6b7`). It pins this repository at the tag `V0.1.0`, commit `a690dc3`, which is on main and 27 commits behind it. It calls `evaluate()` with two gates (hedging and semantic contamination) and does not use the tower, the signer or the ledger. Its default mode is `record`: the verdict is written beside the governance decision and never changes it, and if DIT cannot be imported it records "unavailable" and carries on.
- **Fail behavior.** Closed: failing gates do not emit unsealed text, and refusal is a value (`TowerResult.status`). Gates are regex and heuristic, so false positives and negatives exist. Two defaults are open (EXECUTED 2026-11-18). A tower built with no `signer` signs with a random key made for that one process (key id `ephemeral-...`, and `metadata["ephemeral_signature"]` is true), so its signatures cannot be checked once the process ends. A tower given an empty gate list releases any text. A lasting key is used only when the caller passes `StasisSigner.from_env()`, which reads it from an environment variable with no HSM and raises `MissingSigningKey` when it is absent.

EXECUTED 2026-11-18 at `5e2e290`, Python 3.13, fresh environments. `pip install -e ".[dev]"` then `pytest`: 161 passed, 2 skipped (the two skipped modules need CNS). Re-run 2026-11-19 at `59e9b25`: 161 passed, 2 skipped. With the `cns` extra and `DIT_REQUIRE_CNS=1`, as CI's second job runs it: 196 passed, none skipped, at CNS `v4.0.0` (the pin then) and at `v4.1.0`. `python -m dit` and both `legacy/` scripts exit 0. The earlier line here ("196 passed", 2026-11-15) is the with-CNS count. Not run: CI itself, Python 3.11 and 3.12.

## 1. Pipeline Position & Role

**OUTPUT INTEGRITY** (post-generation, pre-downstream-trust). Complements Conservation Kernel (transformation conservation) and ANVIL (execution lineage). Consumed by [`sentinel_os`](https://github.com/wking53214/sentinel_os) `epistemic/dit_gate.py` (pinned to the tag `V0.1.0`, commit `a690dc3`; evaluate() API; this line used to name `26cee7b9`). **Not** a stage in the observe-perceive orchestrator chain.

```text
generator → oscillation guard → gate stack → normalizer → kinetic governor → HMAC-SHA256 signer (key ID recorded) → optional HashChainLedger → TowerResult
```

## 2. Full System Scope & Architectural Depth

Assembly of recovered GSA v13 Citadel processor + Deterministic Policy Runtime, with Tier 1 audit findings closed.

| Piece | Status |
|---|---|
| `src/dit/` | Live tower |
| `legacy/gsa_v13_citadel_processor.py` | Recovered engine, defects included; test control only |
| `legacy/dpr_runtime.py` | Recovered; two documented defects; not imported by tower |

Gates (`FULL_STACK` / `GSA_V13_STACK`): Identity, Hedging, Causality, Semantic contamination, independent predicates over **raw generated text**. The default stack is GSA_V13_STACK (identity, hedging, causality); pass gates=build_stack(rules, FULL_STACK) to add the terminal semantic contamination gate. Retry with instructional delta up to a budget. `run()` returns refusal values; `run_strict()` raises (`TowerCollapse`) for the historical GSA v13 contract.

`StasisSigner.from_env()` HMAC-SHA256, key from `DIT_STASIS_KEY`, key ID from `DIT_STASIS_KEY_ID`. Missing key → `MissingSigningKey`. `HashChainLedger.verify()` recomputes; tamper → `LedgerTampered`. `KineticGovernor` paces release. `OscillationGuard` SHA-256 digests bounded loops.

Lineage: CITADEL regex enforcer → this tower. CITADEL remains an archive.

## 3. What It Does NOT Do / Non-Goals

- Does not decide policy or authorize execution.
- Does not prove the generator's claim is true.
- Regex/heuristic gates ≠ semantic understanding. Hedging/identity/causality patterns can false-positive and false-negative.
- Does not replace Conservation Kernel propositions.

## 4. Brutally Honest Current Status & Gaps

| Gap | Detail |
|---|---|
| Pattern uncalibrated | `GSA_V13_PATTERNS` / default rules, linguistic, not empirically calibrated on a labeled corpus shipped here. |
| Sentinel pin | sentinel_os pins the tag `V0.1.0` (commit `a690dc3`, on main), so a squash merge can no longer make the pin unreachable. The pin is 27 commits behind main; none of those commits changes `evaluate.py` or `gates.py`, the files that consumer relies on. Checked 2026-11-18. This row used to say sentinel_os pins a branch SHA. |
| HMAC key in env | `KEY_ENV_VAR`; no HSM. Used only when `StasisSigner.from_env()` is passed in; the default signer is a throwaway key (see "Fail behavior" above). |
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
                              ├─ sentinel_os epistemic/dit_gate.py  (LIVE: imported at tag V0.1.0; evaluate() only, record mode by default)
                              └─ observe-perceive                   (not imported)
```

Apache-2.0. Provenance: `docs/PROVENANCE.md`, `docs/AUDIT_REMEDIATION.md`.

## 8. Connecting to CNS (optional)

DIT stands alone: no runtime dependency, and the whole suite passes without
CNS installed. If CNS is present, `dit.cns_connector` expresses DIT's
verdicts as CNS gate results so they can be resolved alongside gates from
other repositories.

```
pip install -e ".[cns]"        # from a clone of this repository
pip install "dit[cns] @ git+https://github.com/wking53214/DIT.git"
```

Do not use the bare form `pip install 'dit[cns]'`, which this section used to show. This package is
not published under that name. An unrelated public package called `dit` (an information-theory
library, version 2.4 on 2026-11-18) would be installed in its place, with no CNS (EXECUTED as a dry
run; the second line above was installed and the example below ran).

```python
from dit.cns_connector import evaluate_to_cns
from cns.gate import resolve

verdicts = evaluate_to_cns(text, subject="reply-1")
resolve(verdicts)        # PASS, RETRY or TERMINAL_BREACH, fail-closed
```

For an actual successful TowerResult, use tower_result_to_cns(tower,
result, subject=...) instead of binding a separate input string. That helper
re-runs the tower's configured gates on the exact released payload and binds
the CNS verdicts to that payload, DIT's native payload digest, signature block,
checksum and optional ledger hash. The helper checks the native signature
with the tower's signer and verifies an attached ledger at the recorded head.
The CNS digest does not establish signer identity or replace that native
evidence; callers needing truncation detection must retain a trusted ledger
head outside the ledger.

| DIT | CNS |
|---|---|
| where it judges | `OMEGA`: the payload as generated. DIT has no precondition end and the connector does not invent one, so `cns_chain(...).complete()` is `False` by design. |
| passed | `PASS` |
| failed, retryable | `RETRY` |
| failed, terminal | `TERMINAL_BREACH` |
| anything else: not a DIT `GateResult`, `passed` not a `bool` (`"no"`), `severity` not a `Severity` member (`"terminal"` as a plain string) | `TERMINAL_BREACH`, never a pass and never downgraded to `RETRY` |
| judged text | `subject` label plus a digest, so a verdict cannot be moved onto other text |

Without CNS installed, the connector's functions raise `CnsNotInstalled` with
the install command. Nothing else in DIT changes. The command that message prints is
still the bare form warned about above; it is in the source code and was not changed here.
