"""
Relay mode helpers: ``ai --server --relay URL`` runs the website, agent runs and tools on this
machine and sends model inference to the Brain Server at URL (see BrainHub relay mode).
"""

import socket
from typing import Optional
from urllib.parse import urlparse


def normalize_relay_url(url: Optional[str]) -> Optional[str]:
    """The Brain Server URL for relay mode, with a scheme and no trailing slash (None when unset)."""
    url = (url or "").strip().rstrip("/")
    if not url:
        return None
    if "://" not in url:
        url = f"http://{url}"
    return url


def is_self_relay(relay_url: str, host: str, port) -> bool:
    """
    True when ``relay_url`` points at this server (same port on a local address): relaying to
    itself would loop every request.
    """
    try:
        parsed = urlparse(relay_url)
        relay_port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError:
        return False
    if relay_port != int(port):
        return False
    relay_host = (parsed.hostname or "").lower()
    local = {"localhost", "0.0.0.0", "::", "::1", "", str(host or "").lower()}
    try:
        hostname = socket.gethostname()
        local.update({hostname.lower(), socket.getfqdn().lower()})
        local.update(socket.gethostbyname_ex(hostname)[2])  # this machine's own IPs
    except OSError:
        pass
    return relay_host in local or relay_host.startswith("127.")
