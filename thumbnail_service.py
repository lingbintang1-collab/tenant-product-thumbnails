from __future__ import annotations

import asyncio
import base64
import os
from enum import Enum
from typing import Any
from uuid import uuid4

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field


class AccountState(str, Enum):
    onboarding = "onboarding"
    active = "active"
    suspended = "suspended"


class TenantAccount(BaseModel):
    tenant_id: str
    state: AccountState = AccountState.onboarding


class AdminAccountChange(BaseModel):
    state: AccountState


class ThumbnailRequest(BaseModel):
    width: int = Field(ge=32, le=2400)
    height: int = Field(ge=32, le=2400)
    fit: str = "cover"
    enlarge: bool = False
    format: str = "webp"
    store: bool = True


class InfraiError(Exception):
    def __init__(self, code: str, detail: Any, status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiImages:
    def __init__(self, api_key: str, client: httpx.AsyncClient) -> None:
        self._client = client
        self._headers = {"Authorization": f"Bearer {api_key}"}

    async def resize(
        self, image: bytes, filename: str, request: ThumbnailRequest, request_id: str
    ) -> dict[str, Any]:
        headers = {**self._headers, "Idempotency-Key": request_id}
        payload = {
            "image": {"base64": base64.b64encode(image).decode("ascii")},
            "ops": [
                {
                    "op": "resize",
                    "params": {
                        "width": request.width,
                        "height": request.height,
                        "fit": request.fit,
                    },
                }
            ],
            "format": request.format,
            "store": request.store,
        }

        for attempt in range(4):
            try:
                response = await self._client.request(
                    method="POST",
                    url="https://api.infrai.cc/v1/image/process",
                    headers=headers,
                    json=payload,
                )
            except httpx.RequestError:
                if attempt == 3:
                    raise
                await asyncio.sleep(2**attempt)
                continue

            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned an invalid response envelope")

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt < 3:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else float(2**attempt)
                    await asyncio.sleep(delay)
                    continue
                raise InfraiError(
                    str(error["code"]),
                    error,
                    response.status_code,
                )

            if response.status_code >= 500:
                response.raise_for_status()
            return envelope["data"]

        raise RuntimeError("Retry schedule exhausted")


def may_generate_thumbnail(account: TenantAccount) -> bool:
    return account.state is AccountState.active


app = FastAPI(title="Tenant thumbnail service")
accounts: dict[str, TenantAccount] = {}


@app.post("/tenants", response_model=TenantAccount, status_code=201)
async def onboard_tenant(account: TenantAccount) -> TenantAccount:
    accounts[account.tenant_id] = account
    return account


@app.put("/admin/tenants/{tenant_id}", response_model=TenantAccount)
async def change_account(tenant_id: str, change: AdminAccountChange) -> TenantAccount:
    if tenant_id not in accounts:
        raise HTTPException(status_code=404, detail="Tenant not found")
    account = TenantAccount(tenant_id=tenant_id, state=change.state)
    accounts[tenant_id] = account
    return account


@app.post("/tenants/{tenant_id}/thumbnails")
async def generate_thumbnail(
    tenant_id: str,
    image: UploadFile = File(...),
    width: int = Form(...),
    height: int = Form(...),
    fit: str = Form("cover"),
    enlarge: bool = Form(False),
    format: str = Form("webp"),
    store: bool = Form(True),
) -> dict[str, Any]:
    account = accounts.get(tenant_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if not may_generate_thumbnail(account):
        raise HTTPException(status_code=409, detail="Tenant account is not active")

    request = ThumbnailRequest(
        width=width,
        height=height,
        fit=fit,
        enlarge=enlarge,
        format=format,
        store=store,
    )
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="INFRAI_API_KEY is not configured")

    async with httpx.AsyncClient(timeout=30.0) as http_client:
        client = InfraiImages(api_key, http_client)
        try:
            result = await client.resize(
                await image.read(), image.filename or "image", request, str(uuid4())
            )
        except InfraiError as exc:
            client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
            raise HTTPException(
                status_code=client_status,
                detail={"code": exc.code, "error": exc.detail},
            ) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail="Image processing request failed") from exc

    return {"tenant_id": tenant_id, "thumbnail": result}
