import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "@/lib/auth";
import type { Permission, SessionInfo } from "@/lib/types";
import { routes } from "./routes";

function session(role: SessionInfo["user"]["role"], permissions: Permission[]): SessionInfo {
  return {
    user: { id: 1, email: "x@example.test", full_name: "Test User", role, blood_bank: null, is_active: true, is_demo: true, last_login_at: null },
    permissions,
    csrf_token: "t",
    expires_at: null,
  };
}

function mockApi(sessionValue: SessionInfo | null) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (url.endsWith("/auth/me")) {
        return sessionValue
          ? new Response(JSON.stringify(sessionValue), { status: 200, headers: { "content-type": "application/json" } })
          : new Response(JSON.stringify({ detail: "Authentication required." }), { status: 401, headers: { "content-type": "application/json" } });
      }
      return new Response(JSON.stringify({ demo_mode: true, unread: 0 }), { status: 200, headers: { "content-type": "application/json" } });
    }),
  );
}

function renderAt(path: string) {
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

afterEach(() => vi.unstubAllGlobals());

describe("route protection", () => {
  it("redirects anonymous users to the login page", async () => {
    mockApi(null);
    const router = renderAt("/donors");
    expect(await screen.findByRole("heading", { name: "Staff sign in" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/login");
  });

  it("shows only permitted navigation items for a bank manager", async () => {
    mockApi(session("bank_manager", ["dashboard:view", "inventory:read", "requests:read", "audit:read"]));
    renderAt("/search");
    const nav = await screen.findByRole("complementary", { name: "Primary navigation" });
    expect(nav).toHaveTextContent("Blood Inventory");
    expect(nav).toHaveTextContent("Audit Logs");
    expect(nav).not.toHaveTextContent("Donors");
    expect(nav).not.toHaveTextContent("User Management");
  });

  it("blocks direct navigation to a page the role cannot access", async () => {
    mockApi(session("coordinator", ["dashboard:view", "donors:read"]));
    renderAt("/users");
    expect(await screen.findByText("Access restricted")).toBeInTheDocument();
  });

  it("shows the synthetic data banner in demo mode", async () => {
    mockApi(session("admin", ["dashboard:view"]));
    renderAt("/search");
    expect(await screen.findByText(/SYNTHETIC DEMO DATA/)).toBeInTheDocument();
  });
});
