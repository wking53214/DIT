import pytest

from dit import KEY_ENV_VAR, MissingSigningKey, StasisSigner
from dit.signing import COMPROMISED_V13_KEY, KEY_ID_ENV_VAR

KEY = b"0123456789abcdef0123456789abcdef"


def test_signature_round_trips():
    signer = StasisSigner(KEY, "k1")
    payload = "Latency fell 12% because batching landed."
    assert signer.verify(payload, signer.sign(payload))


def test_signature_is_hmac_sha256():
    signature = StasisSigner(b"0123456789abcdef", "k1").sign("x")
    assert len(signature) == 64  # 256 bits, hex


def test_tampered_payload_fails_verification():
    signer = StasisSigner(KEY, "k1")
    signature = signer.sign("original")
    assert not signer.verify("original.", signature)


def test_distinct_keys_produce_distinct_signatures():
    a = StasisSigner(b"0123456789abcdefAAAA", "k1").sign("payload")
    b = StasisSigner(b"0123456789abcdefBBBB", "k1").sign("payload")
    assert a != b


def test_signature_block_carries_algorithm_and_key_id():
    block = StasisSigner(KEY, "k1").signature_block("payload")
    assert block["algorithm"] == "hmac-sha256"
    assert block["key_id"] == "k1"
    assert block["value"] == StasisSigner(KEY, "k1").sign("payload")


def test_block_from_the_right_key_checks_out():
    signer = StasisSigner(KEY, "k1")
    block = signer.signature_block("payload")
    assert signer.check_block("payload", block) is None


def test_block_from_another_key_id_is_named_in_the_refusal():
    block = StasisSigner(KEY, "k1").signature_block("payload")
    reason = StasisSigner(KEY, "k2").check_block("payload", block)
    assert reason is not None and "verifier holds 'k2'" in reason


def test_block_with_another_algorithm_is_refused():
    signer = StasisSigner(KEY, "k1")
    block = dict(signer.signature_block("payload"), algorithm="hmac-sha384")
    assert "verifier expects 'hmac-sha256'" in signer.check_block("payload", block)


def test_tampered_block_value_is_refused():
    signer = StasisSigner(KEY, "k1")
    block = signer.signature_block("payload")
    assert signer.check_block("payload.", block) == "signature does not verify"


def test_missing_block_is_refused():
    assert StasisSigner(KEY, "k1").check_block("payload", None) == "no signature present"


def test_the_v13_hardcoded_key_is_refused():
    """The audit's 'Externalize Cryptographic Secrets'.

    The GSA v13.0 key is published in the archive and in this repository's
    own legacy/ directory. A tower that accepted it would be signing with a
    public secret.
    """
    with pytest.raises(ValueError, match="hardcoded key"):
        StasisSigner(COMPROMISED_V13_KEY, "k1")


def test_short_keys_are_refused():
    with pytest.raises(ValueError, match="at least 16 bytes"):
        StasisSigner(b"short", "k1")


def test_non_bytes_key_is_refused():
    with pytest.raises(TypeError):
        StasisSigner("a-string-key-that-is-long-enough", "k1")  # type: ignore[arg-type]


def test_empty_key_id_is_refused():
    with pytest.raises(ValueError, match="key_id"):
        StasisSigner(KEY, "")


def test_from_env_reads_key_and_key_id(monkeypatch):
    monkeypatch.setenv(KEY_ENV_VAR, "an-externally-supplied-secret")
    monkeypatch.setenv(KEY_ID_ENV_VAR, "prod-2026-10")
    signer = StasisSigner.from_env()
    assert signer.key_id == "prod-2026-10"
    assert signer.sign("x")


def test_from_env_names_the_remedy_when_key_unset(monkeypatch):
    monkeypatch.delenv(KEY_ENV_VAR, raising=False)
    monkeypatch.setenv(KEY_ID_ENV_VAR, "prod-2026-10")
    with pytest.raises(MissingSigningKey, match=KEY_ENV_VAR):
        StasisSigner.from_env()


def test_from_env_refuses_a_key_without_an_id(monkeypatch):
    monkeypatch.setenv(KEY_ENV_VAR, "an-externally-supplied-secret")
    monkeypatch.delenv(KEY_ID_ENV_VAR, raising=False)
    with pytest.raises(MissingSigningKey, match=KEY_ID_ENV_VAR):
        StasisSigner.from_env()


def test_generated_keys_are_marked_ephemeral_and_unique():
    first, second = StasisSigner.generate(), StasisSigner.generate()
    assert first.ephemeral
    assert first.key_id.startswith("ephemeral-")
    assert first.key_id != second.key_id
    assert first.sign("payload") != second.sign("payload")
