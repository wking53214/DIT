# Provenance

What DIT was, where the evidence for it lives, and which parts of this
repository are recovery versus reconstruction.

## The name

**DIT — Deterministic Integrity Tower.** The expansion is not inferred. It
appears in the class docstring of the recovered engine:

> `Deterministic Integrity Tower (DIT) Core Engine.`
> — `CitadelProcessor`, GSA v13.0

and in the engine's own banner and terminal error:

> `--- INITIALIZING DETERMINISTIC INTEGRITY TOWER (GSA v13.0) ---`
> `GSA_CRITICAL_ERROR: Deterministic Integrity Tower collapsed. 1.0000 Parity unachievable.`

## Primary sources

All sources are in the owner's Google Drive archive.

| # | Source | Date | What it carries |
|---|---|---|---|
| 1 | `System Audit: Deterministic Integrity Tower - Google Gemini.pdf` (`1P1WUCoXt76wWVdTZlnictEHK16S0dYfO`), chat `1bbb2a96eeb60dd7` | 2026-07-07 | The complete GSA v13.0 engine source, plus the Tier 1 architectural baseline audit of it. The authoritative source for both `legacy/` and `docs/AUDIT_REMEDIATION.md`. |
| 2 | `CLIP (Citadel Linguistic Integrity Pipeline)` (Google Doc, `1H68BI_4SDLMJEqBUzLV7Bu1Ow07BS6yv-z7IOgLq4MY`) | 2026-08-13 | An independent second copy of `CitadelProcessor` and the gate classes, confirming source 1 is not a one-off transcription. Also carries the later `LinguisticComplianceGate` consolidation. |
| 3 | `Iceberg Architecture Dependencies and Missing Modules` (Google Doc, `1_1rmV8OH969BsCBieEJtuLKTTQAvoS-F-jUJ9tAYATg`) | 2026-08-13 | DIT as a layer of the unified Sentinel OS kernel: `sentinel_os/epistemic/dit_gate.py`, `HyperTestTruthProtocol`, the bedrock axioms, and `HashChainLedger` with its 64-zero genesis anchor. |
| 4 | `Citadel: Linguistic Governance Engine - Google Gemini.pdf` (`1LznwGoI27fnN66k1xm_5Ypza-vR3ELW7`) | 2026-07-08 | The Citadel-era antecedent the tower grew out of. |

Two witnesses agree on the v13.0 engine (sources 1 and 2), and a third
independent context (source 3) attests the name and the epistemic layer.

## Recovered, verbatim

- `legacy/gsa_v13_citadel_processor.py` — the complete v13.0 engine from
  source 1, including its simulation runner. It executes and reproduces the
  historical behaviour, collapse included.
- `GSA_V13_PATTERNS` in `src/dit/rules.py` — the five regex patterns,
  character for character, with the original G-stratum comments.
- The 0.815 kinetic coefficient, the 15 ms latency floor, the 200 ms pause
  ceiling, the 5-attempt budget, and the `1.0000` parity scalar.
- `GENESIS = "0" * 64` and canonical-JSON record hashing, from source 3.
- The `semantic_contamination` vocabulary (`feel`, `hope`, `believe`) and
  its terminal-breach semantics, from source 3.

## Reconstructed

These are engineering decisions made here. The archive establishes the
requirement; the implementation is new.

| Component | Basis |
|---|---|
| `RuleSet`, gate injection | The audit's "Decouple Rule Definition Frameworks". |
| `OscillationGuard` | The audit's two memory findings. The bounded-LRU-plus-TTL shape is one of several the audit's "Implement Memory Eviction Guardrails" would accept. |
| `TowerResult` / `Status` | The audit's "Brittle Exception-Driven Flow Control" and "Structure Domain Metrics Objects". The historical dict shape is recoverable via `result.as_dict()`. |
| `StasisSigner` | The audit's "Externalize Cryptographic Secrets". The env var name `DIT_STASIS_KEY` is new. |
| `injection.py` | The audit's prompt-injection and prompt-bloat findings. The control-token neutralisation strategy is new. |
| `Telemetry` | The audit's "Standardize Internal System Telemetry". |
| `TowerConfig` profiles | New. The archive has constants, not profiles. |

## Where the audit was wrong

The 2026-07-07 audit's **Destructive Normalization Ordering** finding
illustrates itself with:

> If an LLM response includes a phrase such as "The framework was optimized
> due to high load", the normalizer forcefully converts the abstract verb,
> yielding "The framework was use due to high load".

It does not. The recovered pattern is `\b(improve|optimize|…)\b`; the
trailing `d` in "optimized" defeats the word boundary, so nothing is
rewritten. The illustration is wrong.

The finding is still worth acting on. Against the v13.0 rule set the
ordering is harmless — none of the eight prohibited verbs is a pronoun, a
hedge, a causal connective, or a digit, so the rewrite cannot change a gate
outcome. But that is a property of one rule set, not of the design, and the
whole point of making rules injectable is that deployments will write their
own. `dit` gates the payload as generated and normalizes on release, which
makes the hazard unreachable regardless of rule set.

`tests/test_audit_findings.py::test_should_fix_normalization_phase_order`
pins both halves: the audit's illustration failing to reproduce, and the
hazard reproducing under a rule set where it is live.

## Version

`13.1.0`. The major version is the recovered engine's (`GSA v13.0`); the
minor marks the remediation pass. This is not a claim of continuous version
history — there is none — it is a statement about what the code descends
from.
