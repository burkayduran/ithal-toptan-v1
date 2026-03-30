const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "auth_token";

const MAX_RETRIES = 2;
const RETRY_DELAY = 1000; // ms

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

/** Save a token to localStorage (pass null to clear). */
export function storeToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

/** Extract a human-readable message from a backend error response. */
async function parseError(res: Response): Promise<string> {
  try {
    const json = await res.json();
    const detail = json?.detail;
    if (Array.isArray(detail)) {
      // Pydantic validation error array
      return detail.map((e: { msg: string }) => e.msg).join("; ");
    }
    if (typeof detail === "string") return detail;
    if (typeof json?.message === "string") return json.message;
  } catch {
    // ignore – fall through to generic message
  }
  return `HTTP ${res.status} ${res.statusText}`;
}

class ClientError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

async function request<T>(
  method: "GET" | "POST" | "PATCH" | "DELETE",
  path: string,
  body?: unknown
): Promise<T> {
  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      const token = getToken();
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const res = await fetch(`${BASE_URL}${path}`, {
        method,
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });

      // Token expired — logout and trigger auth modal
      // Skip this for auth endpoints (login/register) — their 401 is a
      // credential error, not an expired session.
      const isAuthEndpoint = path === "/api/v1/auth/login" || path === "/api/v1/auth/register";
      if (res.status === 401 && !isAuthEndpoint) {
        const { useAuthStore } = await import("@/features/auth/store");
        const store = useAuthStore.getState();
        store.logout();
        if (typeof window !== "undefined") {
          window.dispatchEvent(new CustomEvent("auth:expired"));
        }
        throw new ClientError("Oturumunuz sona erdi. Lütfen tekrar giriş yapın.", 401);
      }

      // 4xx errors — don't retry (client errors)
      if (res.status >= 400 && res.status < 500) {
        const message = await parseError(res);
        throw new ClientError(message, res.status);
      }

      // 5xx errors — retry
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      if (res.status === 204) return undefined as T;
      return res.json() as Promise<T>;
    } catch (error) {
      lastError = error as Error;

      // Don't retry client errors (4xx)
      if (lastError instanceof ClientError) throw lastError;

      // Wait and retry for 5xx / network errors
      if (attempt < MAX_RETRIES) {
        await new Promise((r) => setTimeout(r, RETRY_DELAY * (attempt + 1)));
      }
    }
  }

  throw lastError ?? new Error("Request failed");
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, body),
  delete: <T>(path: string) => request<T>("DELETE", path),
};
