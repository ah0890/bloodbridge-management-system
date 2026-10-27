import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { vi } from "vitest";
import { routes } from "@/app/routes";
import { AuthProvider } from "@/lib/auth";
import type { Permission, Role, SessionInfo } from "@/lib/types";

export function makeSession(role: Role, permissions: Permission[]): SessionInfo {
  return {
    user: { id: 1, email: "x@example.test", full_name: "Test User", role, blood_bank: null, is_active: true, is_demo: true, last_login_at: null },
    permissions,
    csrf_token: "t",
    expires_at: null,
  };
}

type Handler = (url: URL, init?: RequestInit) => unknown | Response;

/** Route-based fetch mock. Unmatched paths return 404 so missing mocks show up as error states. */
export function mockFetch(handlers: Record<string, Handler>) {
  const calls: { method: string; url: URL; body?: unknown }[] = [];
  const fn = vi.fn(async (input: string, init?: RequestInit) => {
    const url = new URL(input, "http://localhost");
    const path = url.pathname.replace(/^\/api\/v1/, "");
    const method = init?.method ?? "GET";
    calls.push({ method, url, body: init?.body ? JSON.parse(String(init.body)) : undefined });
    const key = Object.keys(handlers).find((k) => {
      const [m, p] = k.includes(" ") ? k.split(" ") : ["GET", k];
      return m === method && new RegExp(`^${p}$`).test(path);
    });
    if (!key) return json({ detail: "Not found" }, 404);
    const out = handlers[key](url, init);
    return out instanceof Response ? out : json(out);
  });
  vi.stubGlobal("fetch", fn);
  return calls;
}

export function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}

export function renderApp(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryClientProvider>,
  );
  return router;
}
