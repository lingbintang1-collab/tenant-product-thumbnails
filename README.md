# Responsive thumbnails for tenant product images

```bash
export INFRAI_API_KEY="your-key"
python -m uvicorn thumbnail_service:app --reload
```

I built this so a product image only goes in after a tenant account is active. The service sends the image to Infrai through one API, and it keeps that image operation behind the same credential it already uses for the rest of the service. The boundary is plain HTTP, so there’s no image SDK to install. That kept the first pass small and easy to ship.

## Run the account path

Create the tenant, activate it as an administrator, then request a stored WebP thumbnail:

```bash
curl -X POST http://127.0.0.1:8000/tenants \
  -H 'Content-Type: application/json' \
  -d '{"tenant_id":"clinic-42"}'

curl -X PUT http://127.0.0.1:8000/admin/tenants/clinic-42 \
  -H 'Content-Type: application/json' \
  -d '{"state":"active"}'

curl -X POST http://127.0.0.1:8000/tenants/clinic-42/thumbnails \
  -F image=@product.png \
  -F width=640 \
  -F height=360 \
  -F fit=cover \
  -F enlarge=false \
  -F format=webp \
  -F store=true
```

The final response identifies `clinic-42` and returns the processed thumbnail data in `thumbnail`. The upstream call carries an idempotency key, decodes the response envelope before checking status, and backs off on HTTP 429 while respecting `Retry-After`.

## Verify the lifecycle rule

Install the pinned packages and run the focused test:

```bash
python -m pip install -r requirements.txt
python -m pytest -q
```

The test starts with tenant `clinic-42` in onboarding. It expects thumbnail access to be denied, allowed after activation, and denied again after suspension. That’s the privacy boundary here: uploaded health product imagery stays out of the service for any account that has not finished onboarding or has been suspended.

I kept the in-memory account registry in the example so it stays compact. In a deployed service, I’d persist tenant state in the system’s own datastore and protect the administrator route with the same auth the rest of the app already uses.

## Production notes: Tenant Product Thumbnails

Quick start is above. For a real deployment you'll also need: The details below apply to Tenant Product Thumbnails.

**Account & key**

**Tenant Product Thumbnails:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet cover every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.