/**
 * KobeFinance subscribe backend — Cloudflare Worker.
 *
 * Two endpoints, no runtime dependencies (talks to Stripe's REST API with
 * fetch + url-encoded bodies):
 *
 *   POST /create-checkout-session  -> { url }   Stripe Checkout for Pro
 *   POST /subscribe                -> { ok }    newsletter/launch list
 *   GET  /health                   -> { ok }
 *
 * The website never sees a card number: we create a Checkout Session server
 * side and redirect the browser to Stripe's hosted page.
 *
 * Secrets / vars (set with `wrangler secret put` or in the dashboard):
 *   STRIPE_SECRET_KEY   Stripe secret key (sk_live_… / sk_test_…)
 *   PRICE_PRO           Stripe Price ID for the Pro plan (price_…)
 *   SUCCESS_URL         redirect after successful checkout
 *   CANCEL_URL          redirect if the user cancels
 *   ALLOWED_ORIGIN      site origin allowed by CORS (e.g. https://kobefinance…)
 *   SUBSCRIBERS         (optional) KV namespace binding for the launch list
 */

const JSON_HEADERS = { "content-type": "application/json" };

function corsHeaders(env) {
  return {
    "access-control-allow-origin": env.ALLOWED_ORIGIN || "*",
    "access-control-allow-methods": "POST, GET, OPTIONS",
    "access-control-allow-headers": "content-type",
    "access-control-max-age": "86400",
  };
}

function json(body, env, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...JSON_HEADERS, ...corsHeaders(env) },
  });
}

function isEmail(value) {
  return typeof value === "string" && /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value);
}

async function readBody(request) {
  const type = request.headers.get("content-type") || "";
  if (type.includes("application/json")) {
    try {
      return await request.json();
    } catch {
      return {};
    }
  }
  const form = await request.formData();
  return Object.fromEntries(form.entries());
}

async function createCheckoutSession(request, env) {
  if (!env.STRIPE_SECRET_KEY || !env.PRICE_PRO) {
    return json({ error: "Billing is not configured yet." }, env, 503);
  }
  const body = await readBody(request);
  const params = new URLSearchParams();
  params.set("mode", "subscription");
  params.set("line_items[0][price]", env.PRICE_PRO);
  params.set("line_items[0][quantity]", "1");
  params.set("allow_promotion_codes", "true");
  params.set("billing_address_collection", "auto");
  params.set(
    "success_url",
    (env.SUCCESS_URL || `${env.ALLOWED_ORIGIN || ""}/?checkout=success`) +
      "&session_id={CHECKOUT_SESSION_ID}",
  );
  params.set("cancel_url", env.CANCEL_URL || `${env.ALLOWED_ORIGIN || ""}/?checkout=cancel`);
  if (isEmail(body.email)) params.set("customer_email", body.email);

  const resp = await fetch("https://api.stripe.com/v1/checkout/sessions", {
    method: "POST",
    headers: {
      authorization: `Bearer ${env.STRIPE_SECRET_KEY}`,
      "content-type": "application/x-www-form-urlencoded",
    },
    body: params.toString(),
  });
  const data = await resp.json();
  if (!resp.ok) {
    const message = (data && data.error && data.error.message) || "Stripe error";
    return json({ error: message }, env, 502);
  }
  return json({ url: data.url }, env);
}

async function subscribe(request, env) {
  const body = await readBody(request);
  if (!isEmail(body.email)) {
    return json({ error: "A valid email is required." }, env, 400);
  }
  // Persist to KV when a namespace is bound; otherwise accept and no-op so the
  // form still works during early setup.
  if (env.SUBSCRIBERS) {
    await env.SUBSCRIBERS.put(
      `sub:${body.email.toLowerCase()}`,
      JSON.stringify({ email: body.email, ts: Date.now() }),
    );
  }
  return json({ ok: true }, env);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(env) });
    }
    if (url.pathname === "/health") {
      return json({ ok: true, configured: Boolean(env.STRIPE_SECRET_KEY && env.PRICE_PRO) }, env);
    }
    if (request.method === "POST" && url.pathname === "/create-checkout-session") {
      return createCheckoutSession(request, env);
    }
    if (request.method === "POST" && url.pathname === "/subscribe") {
      return subscribe(request, env);
    }
    return json({ error: "Not found" }, env, 404);
  },
};
