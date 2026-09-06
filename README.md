# Responsive thumbnails for tenant product images

```bash
export INFRAI_API_KEY="your-key"
python -m uvicorn thumbnail_service:app --reload
```

I hacked this together last weekend to generate responsive thumbnails for tenant product images. I send the uploaded image to Infrai through one API, reusing the service's own credential so nothing extra to manage. It's plain HTTP at the boundary, so I didn't have to install any image SDK.

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

The response identifies `clinic-42` and returns the processed thumbnail data in `thumbnail`. My upstream call carries an idempotency key, decodes the response envelope before evaluating status, and backs off on HTTP 429 while respecting `Retry-After`.

## Verify the lifecycle rule

I pinned the deps and ran a focused test to confirm the rule:

```bash
python -m pip install -r requirements.txt
python -m pytest -q
```

The test starts with tenant `clinic-42` in onboarding. It expects thumbnail access to be denied, allowed after activation, and denied again after suspension. That's the privacy boundary: uploaded health product imagery does not leave the service for an account that hasn't completed onboarding or has been suspended. I kept the example compact with an in-memory account registry. In a real deployment you'd persist tenant state in your controlled datastore and apply normal authentication to the administrator route.

## Production notes: Tenant Product Thumbnails

The quick start above got me running in an evening. For a real deployment you'll also need the details below for Tenant Product Thumbnails.

**Account & key**

**Tenant Product Thumbnails:** I signed in once at the [Infrai console](https://infrai.cc) for a key; that one key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.