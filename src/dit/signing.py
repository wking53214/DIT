"""Stasis signatures.

Every payload the tower releases is signed, so a downstream consumer can
prove the text it holds is the text that passed the gates.

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

from .results import MissingSigningKey

#: Environment variable read by :meth:`StasisSigner.from_env`.
KEY_ENV_VAR = "DIT_STASIS_KEY"

#: The key hardcoded in GSA v13.0. Present only so that
#: ``tests/test_audit_findings.py`` can assert it is absent from the
#: package's runtime path, and so a caller re-verifying a historical
#: signature can do so deliberately.
COMPROMISED_V13_KEY = b"GSA_ADAMANTIUM_CORE_STASIS_SIGNATURE_815"


class StasisSigner:
    """HMAC-SHA384 over released payloads."""

    def __init__(self, key: bytes, *, ephemeral: bool = False) -> None:
        if not isinstance(key, (bytes, bytearray)):
            raise TypeError("signing key must be bytes")
        if len(key) < 16:
            raise ValueError("signing key must be at least 16 bytes")
        if bytes(key) == COMPROMISED_V13_KEY:
            raise ValueError(
                "refusing the GSA v13.0 hardcoded key: it is published in "
                "the archive and in legacy/gsa_v13_citadel_processor.py"
            )
        self._key = bytes(key)
        self.ephemeral = ephemeral

    @classmethod
    def from_env(cls, var: str = KEY_ENV_VAR) -> "StasisSigner":
        """Build from ``$DIT_STASIS_KEY``. Raises if it is unset or empty."""
        raw = os.environ.get(var)
        if not raw:
            raise MissingSigningKey(
                f"{var} is unset. Set it to a secret of at least 16 bytes, "
                "or construct StasisSigner.generate() for a process-local key "
                "whose signatures do not survive a restart."
            )
        return cls(raw.encode("utf-8"))

    @classmethod
    def generate(cls) -> "StasisSigner":
        """A random process-local key.

        Signatures are verifiable within this process only. Suitable for
        tests and single-process tools; a signature that must outlive the
        process needs :meth:`from_env` or an explicit key.
        """
        return cls(secrets.token_bytes(48), ephemeral=True)

    def sign(self, payload: str) -> str:
        return hmac.new(
            self._key, payload.encode("utf-8"), hashlib.sha384
        ).hexdigest()

    def verify(self, payload: str, signature: str) -> bool:
        """Constant-time comparison, so a caller cannot time-probe the key."""
        return hmac.compare_digest(self.sign(payload), signature)
