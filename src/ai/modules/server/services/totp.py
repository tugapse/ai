"""
Time-based one-time codes (RFC 6238, the format authenticator apps use) for approving the most
dangerous agent tools. Pure standard library: HMAC-SHA1, 30-second steps, 6 digits.

The secret lives in a file only the server user can read and is created from the server's own
terminal (``ai --server-totp-setup``), so a web client can never read or replace it.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import struct
import threading
import time
from typing import Optional
from urllib.parse import quote

STEP = 30
DIGITS = 6
WINDOW = 1  # accept the previous and next step too (clock drift)


def generate_secret() -> str:
    """A random 160-bit secret in base32, as authenticator apps expect."""
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def code_at(secret: str, counter: int) -> str:
    key = base64.b32decode(secret.upper() + "=" * (-len(secret) % 8))
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(value % 10 ** DIGITS).zfill(DIGITS)


def provisioning_uri(secret: str, account: str = "server", issuer: str = "Jarvis") -> str:
    """The otpauth:// URI an authenticator app imports (as text or a QR code)."""
    return (f"otpauth://totp/{quote(issuer)}:{quote(account)}?secret={secret}"
            f"&issuer={quote(issuer)}&digits={DIGITS}&period={STEP}")


class TotpGuard:
    """Checks codes against the stored secret; a code is accepted once (no replay)."""

    def __init__(self, path: str, clock=time.time):
        self.path = path
        self.clock = clock
        self._lock = threading.Lock()
        self._last_counter = -1

    @property
    def enabled(self) -> bool:
        return self._secret() is not None

    def _secret(self) -> Optional[str]:
        try:
            with open(self.path, encoding="utf-8") as f:
                return json.load(f).get("secret") or None
        except (FileNotFoundError, ValueError, OSError):
            return None

    def setup(self) -> str:
        """Creates (or replaces) the secret; returns it. Old authenticator entries stop working."""
        secret = generate_secret()
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"secret": secret, "created": int(self.clock())}, f)
        os.chmod(self.path, 0o600)
        return secret

    def verify(self, code: Optional[str]) -> bool:
        secret = self._secret()
        code = (code or "").replace(" ", "")
        if secret is None or len(code) != DIGITS or not code.isdigit():
            return False
        now = int(self.clock()) // STEP
        with self._lock:
            for counter in range(now - WINDOW, now + WINDOW + 1):
                if counter > self._last_counter and hmac.compare_digest(code_at(secret, counter), code):
                    self._last_counter = counter
                    return True
        return False
