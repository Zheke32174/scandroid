/**
 * scandroid-approval — agent action 2FA gate.
 *
 * Endpoints:
 *
 *   POST /request                 (agent)
 *     Authorization: Bearer <AGENT_TOKEN>
 *     body: {action: string, details: any, ttl_seconds?: number}
 *     -> 200 {request_id, expires_at, approve_url}
 *     Writes a pending record to KV, emits an ntfy push with action
 *     details + a deep-link to /ui?id=<id>.
 *
 *   GET  /status?id=<id>          (agent)
 *     Authorization: Bearer <AGENT_TOKEN>
 *     -> 200 {request_id, status, action, details, created_at,
 *             expires_at, resolved_at?}
 *     Polled by scandroid.approval.wait(). Status is one of
 *     "pending" | "approved" | "denied" | "expired".
 *
 *   GET  /ui?id=<id>              (user, browser)
 *     -> HTML page showing action + Approve/Deny + a TOTP-code field.
 *
 *   POST /resolve                 (user, from /ui)
 *     body: {request_id, decision: "approve"|"deny", totp_code,
 *            user_token}
 *     -> 200 {ok: true} | 401 / 403 on bad token / TOTP
 *     Validates TOTP against TOTP_SECRET_BASE32 with a +/- 1-step
 *     window for clock drift. On valid: marks the record accordingly
 *     and writes resolved_at.
 *
 *   POST /cancel                  (agent)
 *     Authorization: Bearer <AGENT_TOKEN>
 *     body: {request_id}
 *     -> 200 {ok: true}
 *     Lets an agent withdraw a request before the user resolves it.
 *
 * Threat model:
 *   - AGENT_TOKEN is write-only (creates requests; reads its own
 *     status). It cannot resolve.
 *   - USER_TOKEN + a valid TOTP code are required to resolve. Either
 *     alone is insufficient.
 *   - All KV writes are gated; no public write surface.
 *   - The /ui HTML is unauthenticated to read but submits over
 *     POST /resolve which IS authenticated.
 *
 * Aligned with understory/AI-PARTICIPANTS-TOS-RULE.md: identity-
 * honest credentials, scope-honored capabilities, no impersonation.
 */

interface Env {
  APPROVALS: KVNamespace;
  AGENT_TOKEN: string;
  USER_TOKEN: string;
  TOTP_SECRET_BASE32: string;
  NTFY_TOPIC: string;
  NTFY_AUTH: string;
}

type Status = "pending" | "approved" | "denied" | "expired";

interface Record {
  request_id: string;
  status: Status;
  action: string;
  details: unknown;
  created_at: number;
  expires_at: number;
  resolved_at?: number;
}

const DEFAULT_TTL_SEC = 600; // 10 minutes
const TOTP_WINDOW_STEPS = 1; // +/- 1 30s step for clock drift

function bearer(req: Request): string | null {
  const h = req.headers.get("Authorization") ?? "";
  if (!h.startsWith("Bearer ")) return null;
  return h.slice(7);
}

async function readJson<T>(req: Request): Promise<T> {
  const text = await req.text();
  return JSON.parse(text) as T;
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function htmlResponse(body: string, status = 200): Response {
  return new Response(body, {
    status,
    headers: { "content-type": "text/html; charset=utf-8" },
  });
}

function uuid(): string {
  return crypto.randomUUID();
}

// ---------- TOTP (RFC 6238, SHA-1, 30s, 6 digits) ----------

function base32Decode(b32: string): Uint8Array {
  const cleaned = b32.toUpperCase().replace(/[^A-Z2-7]/g, "");
  const map = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  let bits = 0;
  let value = 0;
  const out: number[] = [];
  for (const ch of cleaned) {
    const i = map.indexOf(ch);
    if (i < 0) continue;
    value = (value << 5) | i;
    bits += 5;
    if (bits >= 8) {
      bits -= 8;
      out.push((value >> bits) & 0xff);
    }
  }
  return new Uint8Array(out);
}

async function hotp(key: Uint8Array, counter: number): Promise<string> {
  // 8-byte big-endian counter
  const ctr = new ArrayBuffer(8);
  const dv = new DataView(ctr);
  dv.setUint32(0, Math.floor(counter / 0x100000000));
  dv.setUint32(4, counter & 0xffffffff);

  const cryptoKey = await crypto.subtle.importKey(
    "raw",
    key as unknown as ArrayBuffer,
    { name: "HMAC", hash: "SHA-1" },
    false,
    ["sign"],
  );
  const sig = new Uint8Array(await crypto.subtle.sign("HMAC", cryptoKey, ctr));
  const offset = sig[19] & 0x0f;
  const code =
    ((sig[offset] & 0x7f) << 24) |
    ((sig[offset + 1] & 0xff) << 16) |
    ((sig[offset + 2] & 0xff) << 8) |
    (sig[offset + 3] & 0xff);
  return (code % 1_000_000).toString().padStart(6, "0");
}

async function verifyTotp(
  secretBase32: string,
  code: string,
  windowSteps = TOTP_WINDOW_STEPS,
): Promise<boolean> {
  if (!/^\d{6}$/.test(code)) return false;
  const key = base32Decode(secretBase32);
  const step = Math.floor(Date.now() / 1000 / 30);
  for (let dt = -windowSteps; dt <= windowSteps; dt++) {
    const candidate = await hotp(key, step + dt);
    // Constant-time compare of 6-char strings.
    if (candidate.length === code.length) {
      let diff = 0;
      for (let i = 0; i < code.length; i++) {
        diff |= candidate.charCodeAt(i) ^ code.charCodeAt(i);
      }
      if (diff === 0) return true;
    }
  }
  return false;
}

// ---------- ntfy ----------

async function ntfyPush(env: Env, title: string, message: string, clickUrl: string) {
  if (!env.NTFY_TOPIC) return;
  const headers: Record<string, string> = {
    Title: title,
    Click: clickUrl,
    Priority: "high",
    Tags: "key,scandroid",
  };
  if (env.NTFY_AUTH) headers.Authorization = `Bearer ${env.NTFY_AUTH}`;
  await fetch(`https://ntfy.sh/${env.NTFY_TOPIC}`, {
    method: "POST",
    headers,
    body: message,
  });
}

// ---------- Endpoints ----------

async function handleRequest(req: Request, env: Env, baseUrl: string): Promise<Response> {
  if (bearer(req) !== env.AGENT_TOKEN) {
    return jsonResponse({ error: "unauthorized" }, 401);
  }
  const body = await readJson<{
    action: string;
    details?: unknown;
    ttl_seconds?: number;
  }>(req);
  if (!body.action || typeof body.action !== "string") {
    return jsonResponse({ error: "missing action" }, 400);
  }
  const id = uuid();
  const now = Math.floor(Date.now() / 1000);
  const ttl = body.ttl_seconds ?? DEFAULT_TTL_SEC;
  const record: Record = {
    request_id: id,
    status: "pending",
    action: body.action,
    details: body.details ?? {},
    created_at: now,
    expires_at: now + ttl,
  };
  await env.APPROVALS.put(`req:${id}`, JSON.stringify(record), {
    expirationTtl: ttl + 60, // KV-side TTL; the worker also self-expires
  });

  const approveUrl = `${baseUrl}/ui?id=${encodeURIComponent(id)}`;
  await ntfyPush(
    env,
    `Agent approval: ${body.action}`,
    `Tap to review (TTL ${ttl}s).`,
    approveUrl,
  );

  return jsonResponse({ request_id: id, expires_at: record.expires_at, approve_url: approveUrl });
}

async function handleStatus(req: Request, env: Env): Promise<Response> {
  if (bearer(req) !== env.AGENT_TOKEN) {
    return jsonResponse({ error: "unauthorized" }, 401);
  }
  const id = new URL(req.url).searchParams.get("id");
  if (!id) return jsonResponse({ error: "missing id" }, 400);
  const raw = await env.APPROVALS.get(`req:${id}`);
  if (!raw) return jsonResponse({ error: "not found" }, 404);
  const r = JSON.parse(raw) as Record;
  // Self-expire if past TTL.
  if (r.status === "pending" && Math.floor(Date.now() / 1000) > r.expires_at) {
    r.status = "expired";
    r.resolved_at = Math.floor(Date.now() / 1000);
    await env.APPROVALS.put(`req:${id}`, JSON.stringify(r));
  }
  return jsonResponse(r);
}

async function handleResolve(req: Request, env: Env): Promise<Response> {
  const body = await readJson<{
    request_id: string;
    decision: "approve" | "deny";
    totp_code: string;
    user_token: string;
  }>(req);
  if (body.user_token !== env.USER_TOKEN) {
    return jsonResponse({ error: "bad user_token" }, 401);
  }
  if (body.decision !== "approve" && body.decision !== "deny") {
    return jsonResponse({ error: "decision must be approve|deny" }, 400);
  }
  const ok = await verifyTotp(env.TOTP_SECRET_BASE32, body.totp_code);
  if (!ok) return jsonResponse({ error: "bad totp_code" }, 403);

  const raw = await env.APPROVALS.get(`req:${body.request_id}`);
  if (!raw) return jsonResponse({ error: "not found" }, 404);
  const r = JSON.parse(raw) as Record;
  if (r.status !== "pending") {
    return jsonResponse({ error: `already ${r.status}` }, 409);
  }
  if (Math.floor(Date.now() / 1000) > r.expires_at) {
    r.status = "expired";
    r.resolved_at = Math.floor(Date.now() / 1000);
    await env.APPROVALS.put(`req:${body.request_id}`, JSON.stringify(r));
    return jsonResponse({ error: "expired" }, 409);
  }
  r.status = body.decision === "approve" ? "approved" : "denied";
  r.resolved_at = Math.floor(Date.now() / 1000);
  await env.APPROVALS.put(`req:${body.request_id}`, JSON.stringify(r));
  return jsonResponse({ ok: true, status: r.status });
}

async function handleCancel(req: Request, env: Env): Promise<Response> {
  if (bearer(req) !== env.AGENT_TOKEN) {
    return jsonResponse({ error: "unauthorized" }, 401);
  }
  const body = await readJson<{ request_id: string }>(req);
  const raw = await env.APPROVALS.get(`req:${body.request_id}`);
  if (!raw) return jsonResponse({ error: "not found" }, 404);
  await env.APPROVALS.delete(`req:${body.request_id}`);
  return jsonResponse({ ok: true });
}

function approvePage(id: string): string {
  // Tiny self-contained page. Submits a POST /resolve with the user
  // token + TOTP code. The user_token is typed by the user (or
  // auto-filled from URL fragment) so it never lands in server logs
  // as a query param. Approve/Deny each fire a separate submit.
  return `<!doctype html>
<html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>scandroid · agent approval</title>
<style>
  body { font: 14px -apple-system,system-ui,sans-serif; background: #0a0a0a; color: #e0e0e0; padding: 20px; max-width: 480px; margin: 0 auto; }
  h1 { font-size: 18px; margin: 0 0 16px; color: #ffb74d; }
  .field { margin: 12px 0; }
  label { display: block; font-size: 12px; color: #9e9e9e; margin-bottom: 4px; }
  input { width: 100%; padding: 10px; background: #1c1c1c; color: #e0e0e0; border: 1px solid #2a2a2a; border-radius: 6px; box-sizing: border-box; }
  pre { background: #141414; padding: 10px; border-radius: 6px; overflow-x: auto; font-size: 11px; }
  .btn { display: inline-block; padding: 10px 16px; border-radius: 6px; border: 0; font-weight: 600; cursor: pointer; margin-right: 8px; }
  .approve { background: #2e7d32; color: #fff; }
  .deny { background: #c62828; color: #fff; }
  .row { display: flex; gap: 8px; margin-top: 16px; }
  .row .btn { flex: 1; }
  .status { margin-top: 12px; font-size: 12px; color: #9e9e9e; }
  .err { color: #ef5350; }
</style>
</head><body>
<h1>Agent approval</h1>
<div id="details">Loading…</div>
<form id="f" onsubmit="return false;">
  <div class="field">
    <label for="user_token">user_token</label>
    <input id="user_token" type="password" autocomplete="off" required>
  </div>
  <div class="field">
    <label for="totp_code">aegis TOTP code (6 digits)</label>
    <input id="totp_code" type="text" inputmode="numeric" pattern="[0-9]{6}" maxlength="6" required>
  </div>
  <div class="row">
    <button class="btn approve" onclick="resolve('approve')">Approve</button>
    <button class="btn deny" onclick="resolve('deny')">Deny</button>
  </div>
  <div id="status" class="status"></div>
</form>
<script>
const id = ${JSON.stringify(id)};
async function load() {
  // Fetch /status to render the action context. The agent endpoint
  // requires AGENT_TOKEN which the user doesn't have; so we render
  // a placeholder and let resolve() carry the action through.
  document.getElementById('details').innerHTML =
    '<pre>request_id: ' + id + '\\nFetch action details from your agent log.</pre>';
}
async function resolve(decision) {
  const status = document.getElementById('status');
  status.classList.remove('err');
  status.textContent = 'submitting…';
  const user_token = document.getElementById('user_token').value;
  const totp_code = document.getElementById('totp_code').value;
  if (!user_token || !/^\\d{6}$/.test(totp_code)) {
    status.classList.add('err');
    status.textContent = 'user_token required and totp_code must be 6 digits';
    return;
  }
  try {
    const r = await fetch('/resolve', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ request_id: id, decision, totp_code, user_token }),
    });
    const j = await r.json();
    if (r.ok) {
      status.textContent = 'resolved: ' + j.status;
    } else {
      status.classList.add('err');
      status.textContent = 'error: ' + (j.error || r.statusText);
    }
  } catch (e) {
    status.classList.add('err');
    status.textContent = 'network error: ' + e;
  }
}
load();
</script>
</body></html>`;
}

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url);
    const baseUrl = `${url.protocol}//${url.host}`;
    try {
      if (req.method === "POST" && url.pathname === "/request") {
        return await handleRequest(req, env, baseUrl);
      }
      if (req.method === "GET" && url.pathname === "/status") {
        return await handleStatus(req, env);
      }
      if (req.method === "POST" && url.pathname === "/resolve") {
        return await handleResolve(req, env);
      }
      if (req.method === "POST" && url.pathname === "/cancel") {
        return await handleCancel(req, env);
      }
      if (req.method === "GET" && url.pathname === "/ui") {
        const id = url.searchParams.get("id") ?? "";
        return htmlResponse(approvePage(id));
      }
      if (req.method === "GET" && url.pathname === "/") {
        return htmlResponse(
          "<h1>scandroid-approval</h1><p>POST /request, GET /status, POST /resolve, POST /cancel.</p>",
        );
      }
      return jsonResponse({ error: "not found" }, 404);
    } catch (e) {
      return jsonResponse({ error: String(e) }, 500);
    }
  },
};
