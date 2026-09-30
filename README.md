# DIT — Deterministic Integrity Tower

A deterministic mediation proxy for probabilistic generators.

Text that cannot satisfy the zero-trust gate stack does not leave the
tower. Text that can leaves normalized, paced, signed, and — when a ledger
is attached — sealed onto a hash chain that a third party can verify
without trusting the tower that wrote it.

```python
import asyncio
from dit import DeterministicIntegrityTower, HashChainLedger, StasisSigner

async def generator(prompt: str) -> str:
    return "Queue depth fell 22% because the batch window was widened."

ledger = HashChainLedger()
tower = DeterministicIntegrityTower(
    generator, signer=StasisSigner.from_env(), ledger=ledger
)

result = asyncio.run(tower.run("Summarize overnight queue behaviour."))
print(result.status.value, result.parity, result.payload)
print(ledger.verify(), result.ledger_hash)
```

```
$ python -m dit
```

## What this repository is

DIT existed in concept before it existed in code. It was designed,
audited, argued with and carried forward across the July–August 2026
archive as a component of the Citadel → GSA → Sentinel OS lineage, but it
was never assembled into a repository of its own.

This repository is that assembly. Two things live here:

- **`legacy/gsa_v13_citadel_processor.py`** — the recovered GSA v13.0
  engine, preserved as found, defects included. It runs. It is imported by
  the test suite as a control and by nothing else.
- **`legacy/dpr_runtime.py`** — the Deterministic Policy Runtime, a second
  recovered artifact from three weeks earlier, on the same terms. It reached
  this repository after the archive it was filed under was lost;
  `docs/PROVENANCE.md` records that route and the two defects it carries.
- **`src/dit/`** — the tower at capacity: the same architecture with every
  finding from its own 2026-07-07 Tier 1 audit closed, and with the
  epistemic gate and hash-chain ledger from the later DIT-era Sentinel OS
  kernel folded back in.

`docs/PROVENANCE.md` records where each piece came from, and which
decisions were reconstruction rather than recovery.

## Why a tower

A language model is a probabilistic device. Everything downstream of it —
an audit trail, a regulatory filing, a decision record — is not. The gap
between those two is where governance systems fail, usually quietly: the
model hedges, the hedge is read as a finding, and nothing in the pipeline
recorded which it was.

DIT closes the gap by refusing to be a filter. A filter edits text until
it looks acceptable. A tower decides whether text may pass, records the
decision, and signs what it released. The distinction matters because only
the second one produces evidence.

## The strata

Each gate is an independent predicate over the payload **as generated**.

| Gate | Stratum | Enforces | On failure |
|---|---|---|---|
| `IdentityGate` | G6 | No first-person perspective | Retry |
| `HedgingGate` | G3 | No epistemic hedging | Retry |
| `CausalityGate` | — | A causal connective **or** a measured quantity | Retry |
| `SemanticContaminationGate` | epistemic | No affective claim (`feel`, `hope`, `believe`) | **Terminal** |

The first three are the recovered GSA v13.0 stack and are retryable: a
failure produces an instructional delta naming what was wrong, and the
generator is asked again. The fourth is from the later DIT gate, whose
bedrock axioms are *Logic > Meaning* and *Truth > Optics*. It is terminal
by design: a generator reporting what it believes has left the evidentiary
frame, and asking it to rephrase returns the same claim in flatter prose.

Around the stack:

- **Oscillation guard** — SHA-256 digests, bounded by count and age, scoped
  to one transaction by default. Catches a generator that has started
  repeating itself.
- **Structure normalizer** — collapses the abstract commercial verb
  vocabulary (`optimize`, `leverage`, `enhance`) to one primitive, on
  release, after the gates have judged the original.
- **Kinetic governor** — paces emission against payload density using the
  historical 0.815 coefficient, so a burst cannot leave the tower faster
  than its consumers were sized for.
- **Stasis signer** — HMAC-SHA384 over the released payload.
- **Hash-chain ledger** — optional, append-only, tamper-evident. Stores
  digests, never payloads, so the trail proves what was released without
  restating it.

## Judging text you already have

The tower is for callers who can re-ask a generator. Some callers cannot:
the API call is over, or the text came out of a record. `evaluate` answers
the one question they have, synchronously, with no loop and no generator.

```python
from dit import evaluate

verdict = evaluate(decision["reasoning"])
if not verdict.passed:
    log.warning("unevidenced prose entering the record: %s", verdict.failures)
```

It returns an `Evaluation` — `passed`, `parity`, per-gate results, and
whether the failure was terminal. The tower gates through the same
`run_stack`, so a caller auditing text with `evaluate` cannot reach a
different verdict than the tower that released it.

Pass your own stack when the default is wrong for the job:

```python
from dit import build_stack, default_rules
from dit.gates import HedgingGate, SemanticContaminationGate

stack = build_stack(default_rules(), (HedgingGate, SemanticContaminationGate))
evaluate(text, stack)
```

## Refusal is a value

```python
result = await tower.run(prompt)
if not result.ok:
    log.warning("refused after %d attempts: %s", result.attempts, result.failures)
```

`run` returns `PASS`, `EXHAUSTED` or `TERMINAL_BREACH`. An exhausted retry
budget is an ordinary operational outcome, not a crash, and `result.parity`
reports how close the final render came. `run_strict` raises
`TowerCollapse` for callers who want the historical GSA v13.0 contract —
with the evidence attached to the exception, which the original did not
provide.

## Install and test

Zero runtime dependencies. Python 3.11+.

```
pip install -e ".[dev]"
pytest
```

141 tests, no services, no network. `tests/test_audit_findings.py` is the
traceability suite: one test per audit finding, each reproducing the defect
against `legacy/` and demonstrating it closed in `dit`.

## Connecting to CNS (optional)

DIT stands alone: no runtime dependency, and the whole suite passes without
CNS installed. If CNS is present, `dit.cns_connector` expresses DIT's
verdicts as CNS gate results so they can be resolved alongside gates from
other repositories.

```
pip install 'dit[cns]'
```

```python
from dit.cns_connector import evaluate_to_cns
from cns.gate import resolve

verdicts = evaluate_to_cns(text, subject="reply-1")
resolve(verdicts)        # PASS, RETRY or TERMINAL_BREACH, fail-closed
```

| DIT | CNS |
|---|---|
| where it judges | `OMEGA`: the payload as generated. DIT has no precondition end and the connector does not invent one, so `cns_chain(...).complete()` is `False` by design. |
| passed | `PASS` |
| failed, retryable | `RETRY` |
| failed, terminal | `TERMINAL_BREACH` |
| judged text | `subject` label plus a digest, so a verdict cannot be moved onto other text |

Without CNS installed, the connector's functions raise `CnsNotInstalled` with
the install command. Nothing else in DIT changes.

## Documentation

- [`docs/PROVENANCE.md`](docs/PROVENANCE.md) — archive sources, what was
  recovered, what was reconstructed, and one place the audit was wrong.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — the pipeline, the
  ordering invariant, and the scale limits that remain.
- [`docs/AUDIT_REMEDIATION.md`](docs/AUDIT_REMEDIATION.md) — the
  finding-by-finding accounting.

## Lineage

```
Citadel (linguistic governance)
   └── CLIP — Citadel Linguistic Integrity Pipeline
        └── GSA v13.0 — CitadelProcessor, "Deterministic Integrity Tower (DIT) Core Engine"
             ├── audited 2026-07-07 (Tier 1 architectural baseline review)
             └── DIT gate — sentinel_os/epistemic/dit_gate.py, HyperTestTruthProtocol
                  └── Sentinel OS — the tower as one layer of a larger kernel
```

`CitadelProcessor` remains available as an alias of
`DeterministicIntegrityTower`, so lineage code reads without translation.

## Licence

Apache 2.0.
