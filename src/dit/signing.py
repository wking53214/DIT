"""Stasis signatures.

Every payload the tower releases is signed, so a downstream consumer can
prove the text it holds is the text that passed the gates.

Signatures are HMAC-SHA256 under a caller-held key, and every signature is
stored with the ``key_id`` of the key that made it, so a verifier knows which
key to ask for. This is the same shape the rest of the portfolio uses
(Conservation_Kernel's ``HmacSigner``).

The recovered engine embedded its HMAC key in the class body
(``b"GSA_ADAMANTIUM_CORE_STASIS_SIGNATURE_815"``), which the 2026-07-07
audit flagged: anyone with the source could forge a stasis signature. The
key is supplied at construction here, read from the environment, or
generated per-process and marked as such.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from typing import Optional

from .results import MissingSigningKey

#: Environment variable read by :meth:`StasisSigner.from_env` for the key.
KEY_ENV_VAR = "DIT_STASIS_KEY"

#: Environment variable read by :meth:`StasisSigner.from_env` for the key ID.
KEY_ID_ENV_VAR = "DIT_STASIS_KEY_ID"

#: The key hardcoded in GSA v13.0. Present only so that
#: ``tests/test_audit_findings.py`` can assert it is absent from the
#: package's runtime path, and so a caller re-verifying a historical
#: signature can do so deliberately.
COMPROMISED_V13_KEY = b"GSA_ADAMANTIUM_CORE_STASIS_SIGNATURE_815"

#: The algorithm name stored beside every signature.
ALGORITHM = "hmac-sha256"


class StasisSigner:
    """HMAC-SHA256 over released payloads, under a named key."""

    algorithm = ALGORITHM

    def __init__(self, key: bytes, key_id: str, *, ephemeral: bool = False) -> None:
        if not isinstance(key, (bytes, bytearray)):
            raise TypeError("signing key must be bytes")
        if len(key) < 16:
            raise ValueError("signing key must be at least 16 bytes")
        if bytes(key) == COMPROMISED_V13_KEY:
            raise ValueError(
                "refusing the GSA v13.0 hardcoded key: it is published in "
                "the archive and in legacy/gsa_v13_citadel_processor.py"
            )
        if not isinstance(key_id, str) or not key_id:
            raise ValueError("signing key needs a non-empty key_id")
        self._key = bytes(key)
        self.key_id = key_id
        self.ephemeral = ephemeral

    @classmethod
    def from_env(
        cls, var: str = KEY_ENV_VAR, key_id_var: str = KEY_ID_ENV_VAR
    ) -> "StasisSigner":
        """Build from ``$DIT_STASIS_KEY`` and ``$DIT_STASIS_KEY_ID``.

        Raises if either is unset or empty. A key without an ID is refused,
        because the ID is what a verifier uses to pick the right key.
        """
        raw = os.environ.get(var)
        if not raw:
            raise MissingSigningKey(
                f"{var} is unset. Set it to a secret of at least 16 bytes, "
                "or construct StasisSigner.generate() for a process-local key "
                "whose signatures do not survive a restart."
            )
        key_id = os.environ.get(key_id_var)
        if not key_id:
            raise MissingSigningKey(
                f"{key_id_var} is unset. Set it to the name of the key in {var}, "
                "so a verifier can tell which key signed a payload."
            )
        return cls(raw.encode("utf-8"), key_id)

    @classmethod
    def generate(cls) -> "StasisSigner":
        """A random process-local key.

        Signatures are verifiable within this process only. Suitable for
        tests and single-process tools; a signature that must outlive the
        process needs :meth:`from_env` or an explicit key.
        """
        key_id = f"ephemeral-{secrets.token_hex(4)}"
        return cls(secrets.token_bytes(48), key_id, ephemeral=True)

    def sign(self, payload: str) -> str:
        return hmac.new(
            self._key, payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()

    def signature_block(self, payload: str) -> dict:
        """The signature as it is stored: algorithm, key ID and value together."""
        return {
            "algorithm": self.algorithm,
            "key_id": self.key_id,
            "value": self.sign(payload),
        }

    def verify(self, payload: str, signature: str) -> bool:
        """Constant-time comparison, so a caller cannot time-probe the key."""
        return hmac.compare_digest(self.sign(payload), signature)

    def check_block(self, payload: str, block: object) -> Optional[str]:
        """None when ``block`` is a valid signature over ``payload`` by this key.

        Otherwise the reason it is not, in words a log can carry.
        """
        if not isinstance(block, dict):
            return "no signature present"
        if block.get("algorithm") != self.algorithm:
            return f"signed with {block.get('algorithm')!r}, verifier expects {self.algorithm!r}"
        if block.get("key_id") != self.key_id:
            return f"signed with key {block.get('key_id')!r}, verifier holds {self.key_id!r}"
        value = block.get("value")
        if not isinstance(value, str) or not self.verify(payload, value):
            return "signature does not verify"
        return None
