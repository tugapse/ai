"""
Who is looking at the open routes (chat sessions): a paired device sees everything; an unpaired
browser sees only the sessions it created, recognised by its ``jarvis_client`` cookie.
"""
from dataclasses import dataclass
from typing import Optional

from ai.modules.server.services.auth import CLIENT_HEADER, CLIENT_ID_COOKIE, COOKIE_NAME, owner_key


@dataclass
class Viewer:
    paired: bool
    owner: Optional[str]   # owner_key of this browser, None for clients without the cookie (CLI)

    def can_see(self, session_owner: Optional[str]) -> bool:
        return self.paired or (self.owner is not None and session_owner == self.owner)

    def can_write(self, session_owner: Optional[str], exists: bool) -> bool:
        """Writing into a session: paired, a new session, the browser's own, or a cookie-less client (CLI)."""
        if self.paired or not exists:
            return True
        if self.owner is None:
            return True   # jarvis CLI clients / relays: unchanged behaviour
        return session_owner == self.owner


def client_id(request) -> Optional[str]:
    """
    The browser's id: from its cookie, or the one the middleware just issued when the request comes
    from the web UI (X-Jarvis-Client) — that response sets the cookie. None for other clients.
    """
    sent = request.cookies.get(CLIENT_ID_COOKIE)
    if sent:
        return sent
    issued = getattr(request.state, "client_id", None)
    return issued if issued and request.headers.get(CLIENT_HEADER) else None


def viewer(request) -> Viewer:
    auth = getattr(request.app.state, "auth", None)
    device = auth.peek_device(request.cookies.get(COOKIE_NAME), request.headers.get("authorization")) if auth else None
    return Viewer(paired=device is not None, owner=owner_key(client_id(request)))
