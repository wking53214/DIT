import pytest

from dit import KEY_ENV_VAR, MissingSigningKey, StasisSigner
from dit.signing import COMPROMISED_V13_KEY


def test_signature_round_trips():
    signer = StasisSigner(b"0123456789abcdef0123456789abcdef")
    payload = "Latency fell 12% because batching landed."
    assert signer.verify(payload, signer.sign(payload))


def test_signature_is_hmac_sha384():
    signature = StasisSigner(b"0123456789abcdef").sign("x")
    assert len(signature) == 96  # 384 bits, hex


def test_tampered_payload_fails_verification():
    signer = StasisSigner(b"0123456789abcdef")
    signature = signer.sign("original")
    assert not signer.verify("original.", signature)


def test_distinct_keys_produce_distinct_signatures():
    a = StasisSigner(b"0123456789abcdefAAAA").sign("payload")
    b = StasisSigner(b"0123456789abcdefBBBB").sign("payload")
    assert a != b


def test_the_v13_hardcoded_key_is_refused():
    """The audit's 'Externalize Cryptographic Secrets'.

    The GSA v13.0 key is published in the archive and in this repository's
    own legacy/ directory. A tower that accepted it would be signing with a
    public secret.
    """
    with pytest.raises(ValueError, match="hardcoded key"):
        StasisSigner(COMPROMISED_V13_KEY)


def test_short_keys_are_refused():
    with pytest.raises(ValueError, match="at least 16 bytes"):
        StasisSigner(b"short")


def test_non_bytes_key_is_refused():
    with pytest.raises(TypeError):
        StasisSigner("a-string-key-that-is-long-enough")  # type: ignore[arg-type]


def test_from_env_reads_the_configured_variable(monkeypatch):
    monkeypatch.setenv(KEY_ENV_VAR, "an-externally-supplied-secret")
    assert StasisSigner.from_env().sign("x")


def test_from_env_names_the_remedy_when_unset(monkeypatch):
    monkeypatch.delenv(KEY_ENV_VAR, raising=False)
    with pytest.raises(MissingSigningKey, match=KEY_ENV_VAR):
        StasisSigner.from_env()


def test_generated_keys_are_marked_ephemeral_and_unique():
    first, second = StasisSigner.generate(), StasisSigner.generate()
    assert first.ephemeral
    assert first.sign("payload") != second.sign("payload")
