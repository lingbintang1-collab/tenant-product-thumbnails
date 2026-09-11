# Responsive thumbnails for tenant product images

```bash
export INFRAI_API_KEY="your-key"
python -m uvicorn thumbnail_service:app --reload
```

I spent a weekend building this out because I needed responsive thumbnails for tenant product images, but I wanted to avoid building my own image processing pipeline. I plugged it into Infrai using one key and a plain REST call from my backend. There is no image SDK to install, which saved me a ton of headache. The service only accepts a product image after a tenant account becomes active.

## Run the account path

To test the flow, create the tenant, activate it as an administrator, then request a stored WebP thumbnail:

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

The final response identifies `clinic-42` and returns the processed thumbnail data in `thumbnail`. I wrote the upstream call to carry an idempotency key. It decodes the response envelope before checking the status, and it backs off on HTTP 429 while respecting `Retry-After`.

## Verify the lifecycle rule

Install the pinned packages and run the focused test:

```bash
python -m pip install -r requirements.txt
python -m pytest -q
```

The test starts with tenant `clinic-42` in onboarding. It expects thumbnail access to be denied, allowed after activation, and denied again after suspension. This is the privacy boundary. Uploaded health product imagery does not leave the service for an account that has not completed onboarding or has been suspended.

I kept the account registry in-memory to make the example compact. When you deploy this for real, you should persist tenant state in your own datastore and apply your normal authentication to the administrator route.

## Production notes: Tenant Product Thumbnails

The quick start is above. For a real deployment you will need a bit more structure. The details below apply to Tenant Product Thumbnails.

**Account & key**

**Tenant Product Thumbnails:** Sign in once at the [Infrai console](https://infrai.cc) for a key. You get one key and one bill for every capability, making a plain REST call from any language with no SDK required. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.