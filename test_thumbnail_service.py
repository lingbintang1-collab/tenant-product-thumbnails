import asyncio
import json
import httpx

from thumbnail_service import (
    AccountState,
    InfraiImages,
    TenantAccount,
    ThumbnailRequest,
    may_generate_thumbnail,
)


def test_only_active_tenant_may_generate_thumbnail() -> None:
    tenant = TenantAccount(tenant_id="clinic-42")
    assert may_generate_thumbnail(tenant) is False

    active = tenant.model_copy(update={"state": AccountState.active})
    assert may_generate_thumbnail(active) is True

    suspended = active.model_copy(update={"state": AccountState.suspended})
    assert may_generate_thumbnail(suspended) is False


def test_resize_sends_contract_compliant_payload() -> None:
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(await request.aread()))
        return httpx.Response(200, json={"ok": True, "data": {"url": "inline"}})

    async def exercise() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await InfraiImages("test-key", client).resize(
                b"image-bytes",
                "product.png",
                ThumbnailRequest(width=640, height=360),
                "request-1",
            )

    asyncio.run(exercise())

    assert set(captured) == {"image", "ops", "format", "store"}
    assert captured["image"] == {"base64": "aW1hZ2UtYnl0ZXM="}
    assert captured["ops"] == [
        {
            "op": "resize",
            "params": {
                "width": 640,
                "height": 360,
                "fit": "cover",
            },
        }
    ]
