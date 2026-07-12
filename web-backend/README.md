# web-backend — subscribe & checkout Worker

A tiny [Cloudflare Worker](https://developers.cloudflare.com/workers/) that backs
the website's **Start Pro** button and **launch-list** form. It has no runtime
dependencies — it calls Stripe's REST API directly.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/create-checkout-session` | Creates a Stripe Checkout Session and returns `{ url }` to redirect to. Optional JSON `{ email }`. |
| `POST` | `/subscribe` | Adds `{ email }` to the launch list (KV, if bound). |
| `GET` | `/health` | `{ ok, configured }` for a quick smoke test. |

The browser never handles card data — checkout happens on Stripe's hosted page.

## Configure

1. **Stripe**: create a product + recurring **Price** for the Pro plan and copy
   the Price ID (`price_…`). Grab your secret key (`sk_test_…` to start).
2. **Secrets** (never commit these):
   ```bash
   npm install
   npx wrangler secret put STRIPE_SECRET_KEY   # sk_test_… / sk_live_…
   npx wrangler secret put PRICE_PRO            # price_…
   ```
3. **Vars**: edit `wrangler.toml` — set `ALLOWED_ORIGIN`, `SUCCESS_URL`,
   `CANCEL_URL` to your deployed site origin.
4. *(Optional)* launch list persistence:
   ```bash
   npx wrangler kv namespace create SUBSCRIBERS
   ```
   Paste the returned id into the `[[kv_namespaces]]` block in `wrangler.toml`.

## Run & deploy

```bash
npm run dev      # local: http://127.0.0.1:8787
npm run deploy   # -> https://kobefinance-subscribe.<subdomain>.workers.dev
```

## Wire the site

In `website/index.html` set `window.KOBE_API` to the deployed Worker URL:

```html
<script>window.KOBE_API = "https://kobefinance-subscribe.<subdomain>.workers.dev";</script>
```

Until that's set (or `/health` reports `configured: false`), the site falls
back to the newsletter form and shows a friendly "billing coming soon" message
instead of failing — safe to ship before Stripe is live.

## Smoke test

```bash
curl -s $KOBE_API/health
curl -s -XPOST $KOBE_API/create-checkout-session -H 'content-type: application/json' -d '{}'
```
