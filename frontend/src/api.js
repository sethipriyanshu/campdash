// Same-origin in production (served by the backend); override with VITE_API_URL in dev.
const BASE = import.meta.env.VITE_API_URL || '';

export const mediaUrl = (path) => (path ? `${BASE}${path}` : '');

async function req(path, opts = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'content-type': 'application/json' },
    ...opts,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = await res.json();
      detail = Array.isArray(j.detail) ? j.detail.map((d) => d.msg).join(', ') : j.detail || detail;
    } catch { /* ignore */ }
    throw new Error(detail);
  }
  return res.status === 204 ? null : res.json();
}

export const getMenu = () => req('/api/menu');

export const getConfig = () => req('/api/config');

export const placeOrder = (payload) =>
  req('/api/orders', { method: 'POST', body: JSON.stringify({ ...payload, idempotency_key: crypto.randomUUID() }) });
