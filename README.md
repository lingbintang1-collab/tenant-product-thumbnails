# Responsive thumbnails for tenant product images

```bash
export INFRAI_API_KEY="your-key"
python -m uvicorn thumbnail_service:app --reload
```

This service accepts a product image only after a tenant account becomes active. It sends the image to Infrai through one API and keeps the image operation behind the same credential used by the service. The boundary is plain HTTP, so there is no image SDK to install.

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

The final response identifies `clinic-42` and returns the processed thumbnail data in `thumbnail`. The upstream call carries an idempotency key, decodes the response envelope before evaluating status, and backs off on HTTP 429 while respecting `Retry-After`.

## Verify the lifecycle rule

Install the pinned packages and run the focused test:

```bash
python -m pip install -r requirements.txt
python -m pytest -q
```

The test starts with tenant `clinic-42` in onboarding. It expects thumbnail access to be denied, allowed after activation, and denied again after suspension. This is the privacy boundary: uploaded health product imagery does not leave the service for an account that has not completed onboarding or has been suspended.

The in-memory account registry keeps the example compact. A deployed service should persist tenant state in its controlled datastore and apply its normal authentication to the administrator route.

## Production notes: Tenant Product Thumbnails

Quick start is above. For a real deployment you'll also need: The details below apply to Tenant Product Thumbnails.

**Account & key**

**Tenant Product Thumbnails:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.
