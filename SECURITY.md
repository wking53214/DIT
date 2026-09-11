# Security

## Reporting

Open a private security advisory on this repository. Do not open a public
issue for a vulnerability.

## What DIT protects

The integrity of text released by a probabilistic generator, and the
evidence that it was released under a known gate configuration.

- **Stasis signatures** (HMAC-SHA384) prove a payload is the one that
  passed the gates.
- **The hash chain** (SHA-256, canonical JSON) makes edits to the
  transaction record detectable.
- **Delta hardening** stops caller text impersonating the tower's own
  control frame on retry.

## What DIT does not protect

- **Confidentiality.** Payloads pass through in the clear. The ledger
  stores digests, but the caller holds the text.
- **The generator.** DIT governs what a generator emits. It cannot
  constrain what the generator does, sees, or sends elsewhere.
- **Semantic truth.** Gates are lexical. Text that satisfies every gate can
  still be wrong.

## Operating requirements

**Set `DIT_STASIS_KEY`.** A tower constructed without a signer generates a
process-local key and marks results `ephemeral_signature: true`. Those
signatures cannot be verified after a restart or by another process.

**Never use the GSA v13.0 key.** `b"GSA_ADAMANTIUM_CORE_STASIS_SIGNATURE_815"`
is published in the archive and in this repository's `legacy/` directory.
`StasisSigner` refuses it.

**Do not import `legacy/`.** It is preserved as a historical control with
its defects intact: hardcoded key, MD5 state hashing, unbounded
cross-transaction loop memory, and an unhardened retry frame. The test
suite imports it deliberately; nothing else should.

**Treat generator output as untrusted.** It reaches the retry prompt, and
the tower assumes it may be hostile. Neutralisation covers the tower's own
control syntax; it is not a general prompt-injection defence for whatever
sits downstream of you.
