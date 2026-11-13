"""
/api/v1/auth/*: pair a device, check it, list and revoke devices.

``require_device`` is the FastAPI dependency every protected route uses.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from ai.modules.server.services.auth import (CLIENT_HEADER, COOKIE_NAME, DEVICE_TTL, AuthError,
                                             AuthService)

router = APIRouter(prefix="/api/v1/auth")


class PairStart(BaseModel):
    device_name: str = ""


class PairFinish(BaseModel):
    pairing_id: str
    code: str
    # CLI clients have no cookie jar: they get the token once in the body and send it as Bearer.
    return_token: bool = False


def _auth(request: Request) -> AuthService:
    service = getattr(request.app.state, "auth", None)
    if service is None:
        raise HTTPException(status_code=503, detail="Authentication not configured.")
    return service


def _ip(request: Request) -> str:
    return request.client.host if request.client else ""


def require_device(request: Request) -> dict:
    """Dependency: the paired device making this request, or 401/403/429."""
    try:
        device = _auth(request).authenticate(
            ip=_ip(request), method=request.method, cookie=request.cookies.get(COOKIE_NAME),
            authorization=request.headers.get("authorization"),
            client_header=request.headers.get(CLIENT_HEADER))
    except AuthError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)
    request.state.device = device
    return device


def _public(device: dict) -> dict:
    return {"device_id": device["device_id"], "name": device["name"], "expires_at": device["expires_at"]}


@router.post("/pair/start")
async def pair_start(payload: PairStart, request: Request):
    """Starts a pairing; the server prints a 6-digit code in its terminal (valid 2 minutes)."""
    try:
        return _auth(request).start_pairing(payload.device_name, _ip(request))
    except AuthError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)


@router.post("/pair/finish")
async def pair_finish(payload: PairFinish, request: Request, response: Response):
    """Checks the code; on success sets the HttpOnly session cookie (or returns the token once)."""
    try:
        token, device = _auth(request).finish_pairing(payload.pairing_id, payload.code, _ip(request))
    except AuthError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)
    response.set_cookie(COOKIE_NAME, token, max_age=DEVICE_TTL, httponly=True, samesite="strict",
                        secure=request.url.scheme == "https", path="/api")
    body = _public(device)
    if payload.return_token:
        body["token"] = token
    return body


@router.get("/me")
async def me(device: dict = Depends(require_device)):
    """The paired device making the request; 401 means show the pairing screen."""
    return _public(device)


@router.post("/logout")
async def logout(request: Request, response: Response, device: dict = Depends(require_device)):
    """Revokes this device and clears its cookie."""
    _auth(request).revoke(device["device_id"], by=device["device_id"], ip=_ip(request))
    response.delete_cookie(COOKIE_NAME, path="/api")
    return {"status": "logged_out"}


@router.get("/devices")
async def devices(request: Request, device: dict = Depends(require_device)):
    return _auth(request).list_devices(current_id=device["device_id"])


@router.delete("/devices/{device_id}")
async def revoke(device_id: str, request: Request, device: dict = Depends(require_device)):
    try:
        _auth(request).revoke(device_id, by=device["device_id"], ip=_ip(request))
    except AuthError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)
    return {"status": "revoked"}
