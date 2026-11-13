"""
Device pairing and protected routes: the real app, AuthService and cookie handling.
"""

import json
import os
import stat

import pytest
from fastapi.testclient import TestClient

from ai.modules.server.app import create_app
from ai.modules.server.services.auth import AuthService, FAILURES_PER_MINUTE, PAIRING_TTL

LOCAL = ("127.0.0.1", 50000)
WEB = {"X-Jarvis-Client": "web"}


class Clock:
    def __init__(self):
        self.now = 1_000_000.0

    def __call__(self):
        return self.now


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def auth(tmp_path, clock):
    return AuthService(None, devices_path=str(tmp_path / "srv" / "devices.json"),
                       audit_path=str(tmp_path / "audit.log"), clock=clock)


@pytest.fixture
def app(hub, auth, tmp_path, monkeypatch):
    monkeypatch.setattr("ai.functions.get_root_directory", lambda: str(tmp_path))
    return create_app(hub, {}, auth=auth)


@pytest.fixture
def browser(app):
    """A browser-like client on localhost: keeps cookies, sends no Authorization."""
    return TestClient(app, client=LOCAL, base_url="http://127.0.0.1:9999")


def pair(client, auth, name="laptop", **extra):
    started = client.post("/api/v1/auth/pair/start", json={"device_name": name}).json()
    code = auth.pairings[started["pairing_id"]]["code"]
    return client.post("/api/v1/auth/pair/finish", json={"pairing_id": started["pairing_id"], "code": code, **extra})


def audit_events(auth):
    return [json.loads(line)["event"] for line in open(auth.audit_path)]


class TestPairing:
    def test_code_is_printed_on_the_server_not_returned(self, browser, auth, capsys):
        started = browser.post("/api/v1/auth/pair/start", json={"device_name": "laptop"}).json()
        assert set(started) == {"pairing_id", "expires_in"} and started["expires_in"] == PAIRING_TTL
        code = auth.pairings[started["pairing_id"]]["code"]
        assert f"{code[:3]} {code[3:]}" in capsys.readouterr().out

    def test_pairing_sets_an_httponly_strict_cookie_and_no_token_in_body(self, browser, auth):
        r = pair(browser, auth)
        assert r.status_code == 200 and "token" not in r.json()
        cookie = r.headers["set-cookie"].lower()
        assert "jarvis_session=" in cookie and "httponly" in cookie and "samesite=strict" in cookie
        assert "path=/api" in cookie
        assert browser.get("/api/v1/auth/me").json()["name"] == "laptop"

    def test_cli_can_ask_for_the_token_once(self, app, auth):
        cli = TestClient(app, client=LOCAL)
        token = pair(cli, auth, return_token=True).json()["token"]
        fresh = TestClient(app, client=LOCAL)
        assert fresh.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200

    def test_device_file_holds_only_the_hash_and_is_private(self, app, auth):
        token = pair(TestClient(app, client=LOCAL), auth, return_token=True).json()["token"]
        text = open(auth.store.path).read()
        assert token not in text and "token_hash" in text
        assert stat.S_IMODE(os.stat(auth.store.path).st_mode) == 0o600

    def test_wrong_code_is_401_and_five_wrong_codes_void_the_pairing(self, browser, auth):
        started = browser.post("/api/v1/auth/pair/start", json={"device_name": "x"}).json()
        code = auth.pairings[started["pairing_id"]]["code"]
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(5):
            r = browser.post("/api/v1/auth/pair/finish", json={"pairing_id": started["pairing_id"], "code": wrong})
            assert r.status_code == 401
        r = browser.post("/api/v1/auth/pair/finish", json={"pairing_id": started["pairing_id"], "code": code})
        assert r.status_code == 404  # voided: the right code no longer works

    def test_expired_pairing_is_410(self, browser, auth, clock):
        started = browser.post("/api/v1/auth/pair/start", json={"device_name": "x"}).json()
        code = auth.pairings[started["pairing_id"]]["code"]
        clock.now += PAIRING_TTL + 1
        r = browser.post("/api/v1/auth/pair/finish", json={"pairing_id": started["pairing_id"], "code": code})
        assert r.status_code == 410

    def test_pairing_is_audited(self, browser, auth):
        pair(browser, auth)
        assert audit_events(auth)[:2] == ["pair_start", "pair_ok"]


class TestProtectedRoutes:
    @pytest.mark.parametrize("method,url", [
        ("post", "/api/v1/shutdown"), ("post", "/api/v1/model/unload"),
        ("delete", "/api/v1/sessions/x.json"), ("put", "/api/v1/sessions/x.json/title"),
        ("post", "/api/v1/prompts"), ("delete", "/api/v1/prompts/x"),
        ("get", "/api/v1/agent/pipelines"), ("get", "/api/v1/auth/devices"),
    ])
    def test_unpaired_is_401(self, browser, method, url):
        assert getattr(browser, method)(url, headers=WEB).status_code == 401

    @pytest.mark.parametrize("url", ["/api/health", "/api/v1/model-configs", "/api/v1/stats",
                                     "/api/v1/sessions", "/api/v1/prompts"])
    def test_reads_stay_open(self, browser, url):
        assert browser.get(url).status_code == 200

    def test_chat_stays_open(self, browser):
        r = browser.post("/api/v1/chat/completions", json={
            "model": "small", "messages": [{"role": "user", "content": "hi"}]})
        assert r.status_code == 200

    def test_cookie_without_client_header_is_403_on_changes(self, browser, auth):
        pair(browser, auth)
        assert browser.post("/api/v1/model/unload").status_code == 403
        assert browser.post("/api/v1/model/unload", headers=WEB).status_code == 200
        assert browser.get("/api/v1/auth/devices").status_code == 200  # reads need no header

    def test_untrusted_network_is_403_even_when_paired(self, app, auth):
        token = pair(TestClient(app, client=LOCAL), auth, return_token=True).json()["token"]
        outside = TestClient(app, client=("8.8.8.8", 1234))
        r = outside.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403 and "denied_network" in audit_events(auth)

    def test_untrusted_network_cannot_start_pairing(self, app):
        outside = TestClient(app, client=("8.8.8.8", 1234))
        assert outside.post("/api/v1/auth/pair/start", json={}).status_code == 403

    def test_failed_attempts_are_rate_limited(self, browser):
        bad = {"Authorization": "Bearer nope"}
        codes = [browser.get("/api/v1/auth/me", headers=bad).status_code for _ in range(FAILURES_PER_MINUTE + 1)]
        assert codes[:FAILURES_PER_MINUTE] == [401] * FAILURES_PER_MINUTE and codes[-1] == 429

    def test_rate_limit_clears_after_a_minute(self, browser, clock):
        bad = {"Authorization": "Bearer nope"}
        for _ in range(FAILURES_PER_MINUTE):
            browser.get("/api/v1/auth/me", headers=bad)
        clock.now += 61
        assert browser.get("/api/v1/auth/me", headers=bad).status_code == 401


class TestDevices:
    def test_expired_device_is_401_and_use_renews_it(self, browser, auth, clock):
        pair(browser, auth)
        first = browser.get("/api/v1/auth/me").json()["expires_at"]
        clock.now += 2 * 3600
        renewed = browser.get("/api/v1/auth/me").json()["expires_at"]
        assert renewed > first
        clock.now = renewed + 1
        assert browser.get("/api/v1/auth/me").status_code == 401

    def test_list_and_revoke_another_device(self, app, browser, auth):
        pair(browser, auth, name="laptop")
        other = TestClient(app, client=LOCAL)
        other_token = pair(other, auth, name="phone", return_token=True).json()["token"]
        devices = browser.get("/api/v1/auth/devices").json()
        assert [(d["name"], d["current"]) for d in devices] == [("laptop", True), ("phone", False)]
        phone = devices[1]["device_id"]
        assert browser.delete(f"/api/v1/auth/devices/{phone}", headers=WEB).json() == {"status": "revoked"}
        assert other.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {other_token}"}).status_code == 401
        assert browser.delete(f"/api/v1/auth/devices/{phone}", headers=WEB).status_code == 404

    def test_logout_revokes_this_device(self, browser, auth):
        pair(browser, auth)
        assert browser.post("/api/v1/auth/logout", headers=WEB).status_code == 200
        assert browser.get("/api/v1/auth/me").status_code == 401
        assert auth.store.devices == {}

    def test_devices_survive_a_restart(self, app, auth, tmp_path, clock):
        token = pair(TestClient(app, client=LOCAL), auth, return_token=True).json()["token"]
        reloaded = AuthService(None, devices_path=auth.store.path, audit_path=auth.audit_path, clock=clock)
        assert reloaded.authenticate("127.0.0.1", "GET", None, f"Bearer {token}", None)["name"] == "laptop"


class TestCors:
    def test_only_configured_origins_get_cors_headers(self, browser):
        ok = browser.options("/api/v1/auth/me", headers={
            "Origin": "http://localhost:4200", "Access-Control-Request-Method": "GET"})
        assert ok.headers.get("access-control-allow-origin") == "http://localhost:4200"
        assert ok.headers.get("access-control-allow-credentials") == "true"
        evil = browser.options("/api/v1/auth/me", headers={
            "Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
        assert "access-control-allow-origin" not in evil.headers

    def test_same_host_other_port_is_allowed(self, app):
        lan = TestClient(app, client=LOCAL, base_url="http://192.168.1.20:9999")
        r = lan.options("/api/v1/auth/me", headers={
            "Origin": "http://192.168.1.20:4200", "Access-Control-Request-Method": "GET"})
        assert r.headers.get("access-control-allow-origin") == "http://192.168.1.20:4200"
        other = lan.options("/api/v1/auth/me", headers={
            "Origin": "http://192.168.1.99:4200", "Access-Control-Request-Method": "GET"})
        assert "access-control-allow-origin" not in other.headers
