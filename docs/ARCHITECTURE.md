# Architecture

## The pipeline

One transaction, in order:

```
prompt
  │
  ├─► generator(prompt)                    caller-supplied, awaited
  │
  ├─► OscillationGuard                     SHA-256 digest; bounded, scoped
  │      └─ repeat? ──────────────────────► retryable failure
  │
  ├─► gate stack, on the raw payload
  │      ├─ IdentityGate            G6      retryable
  │      ├─ HedgingGate             G3      retryable
  │      ├─ CausalityGate           —       retryable
  │      └─ SemanticContamination   epi     TERMINAL — short-circuits
  │
  ├─► StructureNormalizer                   release-time rewrite
  ├─► KineticGovernor                       paced release, 0.815
  ├─► StasisSigner                          HMAC-SHA384
  └─► HashChainLedger                       optional seal
         │
         └─► TowerResult
```

On a retryable failure the reasons accumulate, an instructional delta is
assembled from the whole accumulated set, and the loop runs again up to
`config.max_attempts`. On a terminal failure the transaction ends
immediately; no delta can repair an epistemic breach.

## The ordering invariant

**Gates read the payload as generated. Normalization happens on release.**

This is the single most load-bearing structural decision in the tower, and
it inverts the recovered engine. If normalization runs first, every gate is
judging text the normalizer has already rewritten, and a finding about the
output is a finding about an artefact the tower manufactured.

Two tests hold the invariant:

- `test_normalizer_leaves_gate_vocabulary_untouched` asserts the property
  directly: for the shipped rule set, normalization changes no gate's
  verdict. If this fails, the ordering is no longer merely correct, it is
  load-bearing in a way the code does not document.
- `test_should_fix_normalization_phase_order` constructs a rule set where
  the hazard is live and shows the two orderings diverging.

## Why the epistemic gate is terminal

Every other gate describes a defect in how a claim was phrased. A hedge can
be removed and the claim survives; a pronoun can be dropped and the finding
is unchanged.

`feel`, `hope`, `believe` are different. They describe the generator's
relationship to the claim rather than the claim's relationship to evidence.
Asking for a re-render returns the same unevidenced claim with the marker
filed off, which is strictly worse: the tower would have laundered it.

So the transaction ends, the ledger records `TERMINAL_BREACH`, and the
caller decides. This is the bedrock axiom from the DIT-era gate — *Truth >
Optics* — expressed as control flow.

## Scoping the oscillation guard

`LoopScope.RUN` (default) gives each transaction a fresh guard. Repetition
within one transaction is a looping generator. Repetition across
transactions is two callers asking the same question, which is not a
defect.

`LoopScope.INSTANCE` shares one bounded guard across every run on a tower.
Use it when a tower serves a single stream and repetition across
transactions really is drift. It is bounded by count and age either way, so
neither scope can leak.

## What the ledger stores

Digests, never payloads. A record carries the prompt digest, the payload
digest, the stasis checksum, the status, the parity and the failure
reasons — enough to prove which text was released, not enough to reproduce
it. A tower governing regulated or personal text must not turn its audit
trail into a second copy of the data.

`verify()` recomputes every digest from its record body rather than
comparing stored hash fields to each other. The recovered implementation
did the latter, which meant a record's content could be edited in place
and the chain would still verify.

## Concurrency

Concurrent, not parallel. Every await point yields — the generator call and
the kinetic pause — so transactions on one event loop interleave rather
than queue. For a component whose cost is dominated by waiting on an
upstream inference endpoint, that is the right shape.

## Limits that remain

Stated rather than fixed, because fixing them changes what DIT is.

**Regex evaluation runs on the event-loop thread.** Gating very large
payloads at high volume will show up as event-loop latency. Run towers
across processes.

**No distributed coordination.** `LoopScope.INSTANCE` is per-process. Two
towers in two processes cannot see each other's oscillation history. A
cross-process guard means Redis, and a library that requires Redis is a
service.

**The ledger is in-memory.** `HashChainLedger` holds its chain in a list.
Durable custody is the job of the Sentinel OS ledger stage downstream; DIT
seals a transaction, it does not store it forever.

**Gates are lexical.** They match patterns, not meaning. `CausalityGate`
accepts "revenue rose 3%" and also accepts "3 people disagreed", because
both contain a number. A gate stack is a floor under output quality, not a
substitute for review.

## Two entry points

`DeterministicIntegrityTower.run` and `evaluate` are the same gate
evaluation with different surroundings. The tower adds what only makes
sense when a generator is still reachable: retry with an instructional
delta, oscillation memory across attempts, pacing, signing, sealing.
`evaluate` is the bare judgement.

Both call `run_stack` and `parity_of` in `dit.evaluate`. That sharing is
deliberate and load-bearing: a consumer that audits stored text with
`evaluate` must reach exactly the verdict the tower reached when it
released that text, or the audit trail disagrees with itself.
`test_tower_and_evaluate_agree` pins it.

## Extending

Add a gate by satisfying the `Gate` protocol — a `name` and a
`check(text) -> GateResult`. Set `severity=Severity.TERMINAL` if the
failure is not the kind a re-render can repair. Pass the stack in:

```python
DeterministicIntegrityTower(generator, gates=[*build_stack(rules), MyGate()])
```

Add a rule by building a `RuleSet` from your own mapping. Nothing in the
engine reads a module-level pattern table.
