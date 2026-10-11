"""LEGACY verify-only path for pre-HMAC-SHA256 (SHA-384) signatures."""

import hashlib
import hmac

from dit import StasisSigner

KEY = b"0123456789abcdef0123456789abcdef"


def _sha384(payload: str, key: bytes = KEY) -> str:
    return hmac.new(key, payload.encode("utf-8"), hashlib.sha384).hexdigest()


def test_legacy_sha384_signature_still_verifies():
    signer = StasisSigner(KEY, "k1")
    assert signer.verify_legacy_sha384("released text", _sha384("released text"))


def test_legacy_check_refuses_a_tampered_payload():
    signer = StasisSigner(KEY, "k1")
    assert not signer.verify_legacy_sha384("released text.", _sha384("released text"))


def test_legacy_check_refuses_a_signature_from_another_key():
    signer = StasisSigner(KEY, "k1")
    other = _sha384("released text", key=b"fedcba9876543210fedcba9876543210")
    assert not signer.verify_legacy_sha384("released text", other)


def test_legacy_path_never_produces_a_new_signature():
    signer = StasisSigner(KEY, "k1")
    assert signer.signature_block("payload")["algorithm"] == "hmac-sha256"
    assert len(signer.sign("payload")) == 64  # still SHA-256 length
