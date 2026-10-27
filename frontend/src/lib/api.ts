const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public details?: unknown,
  ) {
    super(message);
  }
}

function readCookie(name: string): string | undefined {
  return document.cookie
    .split("; ")
    .find((c) => c.startsWith(`${name}=`))
    ?.split("=")[1];
}

type Query = Record<string, string | number | boolean | undefined | null | (string | number)[]>;

export function buildQuery(params?: Query): string {
  if (!params) return "";
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    if (Array.isArray(v)) v.forEach((item) => sp.append(k, String(item)));
    else sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

function formatDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d: { loc?: (string | number)[]; msg?: string }) => {
        const field = d.loc?.filter((p) => p !== "body" && p !== "query").join(".");
        return field ? `${field}: ${d.msg}` : (d.msg ?? "Invalid input");
      })
      .join("; ");
  }
  return "Request failed.";
}

async function request<T>(method: string, path: string, body?: unknown, query?: Query): Promise<T> {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (method !== "GET") {
    const csrf = readCookie("bb_csrf");
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }
  const res = await fetch(`${API_BASE}${path}${buildQuery(query)}`, {
    method,
    headers,
    credentials: "include",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (res.status === 204) return undefined as T;
  const isJson = res.headers.get("content-type")?.includes("application/json");
  const data = isJson ? await res.json() : await res.text();
  if (!res.ok) {
    const detail = isJson ? (data as { detail?: unknown }).detail : undefined;
    throw new ApiError(res.status, formatDetail(detail ?? res.statusText), detail);
  }
  return data as T;
}

export const api = {
  get: <T>(path: string, query?: Query) => request<T>("GET", path, undefined, query),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body ?? {}),
  patch: <T>(path: string, body: unknown) => request<T>("PATCH", path, body),
  put: <T>(path: string, body: unknown) => request<T>("PUT", path, body),
  del: <T>(path: string) => request<T>("DELETE", path),
};

/** URL for a CSV download endpoint (browser navigation carries the session cookie). */
export function downloadUrl(path: string, query?: Query): string {
  return `${API_BASE}${path}${buildQuery(query)}`;
}
