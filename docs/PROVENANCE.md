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
| 5 | Gemini Apps Activity export, record `1178`, artifact `core/dpr_runtime.py` | 2026-06-19 | The Deterministic Policy Runtime: intake validation and attestation, three weeks older than the v13.0 engine. Preserved in `legacy/dpr_runtime.py`. |

Two witnesses agree on the v13.0 engine (sources 1 and 2), and a third
independent context (source 3) attests the name and the epistemic layer.

## Recovered, verbatim

- `legacy/gsa_v13_citadel_processor.py` — the complete v13.0 engine from
  source 1, including its simulation runner. It executes and reproduces the
  historical behaviour, collapse included.
- `legacy/dpr_runtime.py` — the complete Deterministic Policy Runtime from
  source 5. It executes as found. The only change from the archived text is
  the substitution of ordinary spaces for the non-breaking spaces the Takeout
  exporter rendered indentation as; without it the file is not valid Python.
  No logic was touched.
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

## The DPR runtime, and the repository that was going to hold it

`legacy/dpr_runtime.py` reached this repository by an indirect route worth
recording.

A separate repository, `GSA-2`, existed to archive a Gemini transcript that
included this artifact among roughly fifteen others. An August 2026
inclusion-floor assessment ran them: two executed cleanly, two more ran
meaningful retry and convergence logic before hitting deliberately designed
exceptions, and the rest failed on syntax or name errors.

`GSA-2` no longer exists. Its GitHub repository is empty and its artifacts are
gone. When the archive was re-examined in September 2026 the DPR runtime was
the one piece of it that could be identified with confidence — and the
activity record carrying it is tagged to the **DIT** notebook, not to any
notebook of its own.

So it was placed here, where its provenance points, rather than used to
reconstitute a repository whose boundary could not be established. Rebuilding
`GSA-2` around DIT-provenance material would have manufactured exactly the
cross-repository duplication this lineage already has too much of. `GSA-2` is
treated as lost.

### What the artifact shows

Two findings, both pinned by `tests/test_dpr_runtime.py`:

**The risk gate is unreachable.** `evaluate_policy` accumulates three weights
— identity 0.15, courtesy 0.10, long payload 0.20 — against a
`MAX_RISK_THRESHOLD` of 0.80. The weights sum to 0.45. No input can reach the
threshold, so `RISK_THRESHOLD_EXCEEDED` is dead code and the runtime's only
live rejection path is its empty-input check. Read casually, the function
appears to refuse high-risk input. It cannot.

**Key handling was better here, and regressed afterwards.** This June artifact
takes its signing key as a constructor argument and its own entrypoint
generates one with `secrets.token_bytes(32)`. The v13.0 engine that followed
it three weeks later carries `GSA_ADAMANTIUM_CORE_STASIS_SIGNATURE_815`
hardcoded — the defect `dit.signing` now refuses by value. The lineage did not
move monotonically toward better practice on this point; it moved away and
back.

## Version

`13.1.0`. The major version is the recovered engine's (`GSA v13.0`); the
minor marks the remediation pass. This is not a claim of continuous version
history — there is none — it is a statement about what the code descends
from.
