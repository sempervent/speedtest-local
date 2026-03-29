/**
 * API origin prefix. Empty / unset = same origin: `apiFetch("/api/...")` hits nginx or the Vite proxy.
 * Set to e.g. `https://api.example` only when the UI is served from a different host than the API.
 */
export function apiBase(): string {
  const v = import.meta.env.VITE_API_BASE_URL;
  if (v === undefined || v === "") return "";
  return String(v).replace(/\/$/, "");
}

export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const base = apiBase();
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;
  return fetch(url, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.headers || {}),
    },
  });
}
