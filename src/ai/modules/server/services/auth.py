"""
Device pairing and request authentication for the server's protected routes.

A device pairs once: it asks for a pairing, the server prints a 6-digit code in its own
terminal, and the device sends the code back. The server then issues a random token for that
device, stores only its SHA-256 hash, and sets it as an HttpOnly cookie (browsers) or returns
it once (CLI clients that send ``Authorization: Bearer``).

Every protected request must also come from a trusted network, and a cookie-authenticated
request that changes state must carry ``X-Jarvis-Client`` (a header a cross-site form cannot
send). Failed attempts are rate limited per IP, and every security event is audited.
"""

import hashlib
import hmac
import ipaddress
import json
import os
import secrets
import threading
import time
import uuid
from collections import defaultdict, deque
from typing import Dict, List, Optional

import ai.functions as func
from ai.config import ProgramSetting
from ai.services.directory_manager import DirectoryManager

COOKIE_NAME = "jarvis_session"
CLIENT_HEADER = "x-jarvis-client"
PAIRING_TTL = 120
PAIRING_MAX_ATTEMPTS = 5
DEVICE_TTL = 30 * 24 * 3600
RENEW_EVERY = 3600              # sliding expiry is written at most once an hour per device
FAILURES_PER_MINUTE = 10
DEFAULT_TRUSTED_NETWORKS = [
    "127.0.0.0/8", "::1/128",                          # this machine
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",   # private LAN
    "100.64.0.0/10",                                   # Tailscale / CGNAT
]


class AuthError(Exception):
    """A refused request; ``status`` is the HTTP code (401, 403, 404, 410, 429)."""

    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status, self.detail = status, detail


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class DeviceStore:
    """Paired devices in a JSON file only the server user can read (mode 600)."""

    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        self.devices: Dict[str, dict] = self._load()

    def _load(self) -> Dict[str, dict]:
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except FileNotFoundError:
            return {}
        except Exception as e:
            func.log(f"Auth: unreadable device file {self.path}: {e}. No device is paired.", level="ERROR")
            return {}

    def save(self) -> None:
        with self._lock:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            tmp = f"{self.path}.tmp"
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self.devices, f, indent=2)
            os.replace(tmp, self.path)

    def by_token(self, token: str) -> Optional[dict]:
        wanted = _hash(token)
        for device in self.devices.values():
            if hmac.compare_digest(device.get("token_hash", ""), wanted):
                return device
        return None


class AuthService:
    """Pairing, token checks, network and rate limits, audit log."""

    def __init__(self, config=None, devices_path: Optional[str] = None, audit_path: Optional[str] = None,
                 clock=time.time, totp_path: Optional[str] = None):
        self.config = config
        self.clock = clock
        directory = DirectoryManager()
        self.store = DeviceStore(devices_path or os.path.join(directory.get_user_directory(), "server", "devices.json"))
        from ai.modules.server.services.totp import TotpGuard
        self.totp = TotpGuard(totp_path or os.path.join(os.path.dirname(self.store.path), "totp.json"), clock=clock)
        self.audit_path = audit_path or os.path.join(directory.get_system_logs_directory(), "server_audit.log")
        self.pairings: Dict[str, dict] = {}
        self._failures: Dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()
        self.networks = self._networks()

    # --- settings --------------------------------------------------------------------

    def _setting(self, key: ProgramSetting, default):
        try:
            value = self.config.get(key) if self.config is not None else None
        except Exception:
            value = None
        return default if value in (None, "", []) else value

    def _networks(self) -> List[ipaddress._BaseNetwork]:
        nets = []
        for cidr in self._setting(ProgramSetting.SERVER_TRUSTED_NETWORKS, DEFAULT_TRUSTED_NETWORKS):
            try:
                nets.append(ipaddress.ip_network(cidr, strict=False))
            except ValueError:
                func.log(f"Auth: ignoring invalid network '{cidr}' in SERVER_TRUSTED_NETWORKS.", level="WARN")
        return nets

    # --- checks ----------------------------------------------------------------------

    def check_network(self, ip: Optional[str]) -> None:
        try:
            address = ipaddress.ip_address(ip or "")
        except ValueError:
            raise AuthError(403, "Request from an unknown address.")
        if not any(address in net for net in self.networks):
            self.audit("denied_network", ip=ip)
            raise AuthError(403, "This network may not use protected routes (SERVER_TRUSTED_NETWORKS).")

    def check_rate(self, ip: str) -> None:
        with self._lock:
            window = self._failures[ip]
            now = self.clock()
            while window and window[0] < now - 60:
                window.popleft()
            if len(window) >= FAILURES_PER_MINUTE:
                raise AuthError(429, "Too many failed attempts. Wait a minute.")

    def fail(self, ip: str, status: int, detail: str, **audit) -> AuthError:
        with self._lock:
            self._failures[ip].append(self.clock())
        self.audit("auth_failed", ip=ip, reason=detail, **audit)
        return AuthError(status, detail)

    # --- pairing ---------------------------------------------------------------------

    def start_pairing(self, device_name: str, ip: str) -> dict:
        self.check_network(ip)
        self.check_rate(ip)
        name = (device_name or "").strip()[:64] or "device"
        pairing_id = uuid.uuid4().hex
        code = f"{secrets.randbelow(10 ** 6):06d}"
        now = self.clock()
        with self._lock:
            self.pairings = {k: v for k, v in self.pairings.items() if v["expires"] > now}
            self.pairings[pairing_id] = {"code": code, "name": name, "expires": now + PAIRING_TTL,
                                         "attempts": 0, "ip": ip}
        self.audit("pair_start", ip=ip, name=name)
        self.announce_code(name, ip, code)
        return {"pairing_id": pairing_id, "expires_in": PAIRING_TTL}

    @staticmethod
    def announce_code(name: str, ip: str, code: str) -> None:
        """Shows the code on the server's terminal only: whoever reads it there is trusted."""
        func.log(f"PAIRING REQUEST from '{name}' ({ip}). Code: {code[:3]} {code[3:]} (valid {PAIRING_TTL // 60} min)",
                 level="WARN")

    def finish_pairing(self, pairing_id: str, code: str, ip: str) -> tuple:
        """Returns (token, device). Raises 401 wrong code, 404 unknown, 410 expired or void."""
        self.check_network(ip)
        self.check_rate(ip)
        with self._lock:
            pairing = self.pairings.get(pairing_id)
        if pairing is None:
            raise self.fail(ip, 404, "Unknown pairing. Start again.")
        if pairing["expires"] <= self.clock() or pairing["attempts"] >= PAIRING_MAX_ATTEMPTS:
            self.pairings.pop(pairing_id, None)
            raise self.fail(ip, 410, "Pairing expired. Start again.")
        if not hmac.compare_digest(pairing["code"], str(code or "").replace(" ", "")):
            pairing["attempts"] += 1
            if pairing["attempts"] >= PAIRING_MAX_ATTEMPTS:
                self.pairings.pop(pairing_id, None)
            raise self.fail(ip, 401, "Wrong code.", name=pairing["name"])
        self.pairings.pop(pairing_id, None)

        token = secrets.token_urlsafe(32)
        now = self.clock()
        device = {"device_id": uuid.uuid4().hex[:12], "name": pairing["name"], "token_hash": _hash(token),
                  "created": now, "last_used": now, "expires_at": now + DEVICE_TTL, "ip": ip}
        self.store.devices[device["device_id"]] = device
        self.store.save()
        self.audit("pair_ok", ip=ip, device_id=device["device_id"], name=device["name"])
        return token, device

    # --- requests --------------------------------------------------------------------

    def authenticate(self, ip: str, method: str, cookie: Optional[str], authorization: Optional[str],
                     client_header: Optional[str]) -> dict:
        """The device a protected request comes from. Raises AuthError otherwise."""
        self.check_network(ip)
        self.check_rate(ip)
        bearer = (authorization or "")
        token = bearer[len("Bearer "):].strip() if bearer.startswith("Bearer ") else ""
        from_cookie = not token and bool(cookie)
        token = token or (cookie or "")
        if not token:
            raise AuthError(401, "Not paired. Pair this device first.")
        device = self.store.by_token(token)
        if device is None:
            raise self.fail(ip, 401, "Unknown or revoked device. Pair again.")
        now = self.clock()
        if device["expires_at"] <= now:
            raise self.fail(ip, 401, "Device pairing expired. Pair again.", device_id=device["device_id"])
        if from_cookie and method.upper() not in ("GET", "HEAD", "OPTIONS") and not client_header:
            # A cross-site form can send the cookie but not a custom header.
            raise self.fail(ip, 403, "Missing X-Jarvis-Client header.", device_id=device["device_id"])
        if now - device.get("last_used", 0) > RENEW_EVERY:
            device["last_used"], device["expires_at"] = now, now + DEVICE_TTL
            self.store.save()
        return device

    def list_devices(self, current_id: Optional[str] = None) -> List[dict]:
        return [{"device_id": d["device_id"], "name": d["name"], "created": d["created"],
                 "last_used": d["last_used"], "expires_at": d["expires_at"],
                 "current": d["device_id"] == current_id}
                for d in sorted(self.store.devices.values(), key=lambda d: d["created"])]

    def revoke(self, device_id: str, by: Optional[str] = None, ip: Optional[str] = None) -> None:
        if self.store.devices.pop(device_id, None) is None:
            raise AuthError(404, f"Device '{device_id}' not found.")
        self.store.save()
        self.audit("revoke", ip=ip, device_id=device_id, by=by)

    # --- audit -----------------------------------------------------------------------

    def audit(self, event: str, **data) -> None:
        """One JSON line per security event (pairing, failures, revokes, agent actions)."""
        record = {"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "event": event,
                  **{k: v for k, v in data.items() if v is not None}}
        try:
            os.makedirs(os.path.dirname(self.audit_path), exist_ok=True)
            with open(self.audit_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            func.log(f"Auth: audit write failed: {e}", level="ERROR")
