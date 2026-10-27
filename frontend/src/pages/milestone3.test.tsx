import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { DonorListItem } from "@/lib/domain";
import { json, makeSession, mockFetch, renderApp } from "@/test/utils";

const coordinator = makeSession("coordinator", ["dashboard:view", "donors:read", "donors:write", "donors:contact", "donors:export", "banks:read"]);

const summary = {
  kpis: {
    registered_donors: 973,
    available_donors: 321,
    available_units: 796,
    active_requests: 34,
    critical_or_overdue_requests: 23,
    verified_blood_banks: 29,
    expiring_units: 85,
    fulfilled_in_period: 12,
    period_start: "2026-09-28",
    period_end: "2026-10-27",
  },
  stock_by_group: { "A+": 198, "A-": 26, "B+": 273, "B-": 9, "AB+": 78, "AB-": 6, "O+": 185, "O-": 21 },
  thresholds: { low_stock_units: 10, expiry_warning_days: 7, availability_fresh_days: 90, whole_blood_deferral_days: 90 },
  scope: { blood_bank_id: null, org_scoped: false },
};

const dashboardHandlers = {
  "/auth/me": () => coordinator,
  "/meta/data-status": () => ({ demo_mode: true }),
  "/blood-banks/cities": () => ["Lahore", "Karachi"],
  "/blood-banks": () => [],
  "/dashboard/summary": () => summary,
  "/dashboard/inventory-health": () => ({ low_stock: [{ blood_group: "B-", units: 9, threshold: 10 }], expiring: [], excluded_units: {}, wasted_last_30_days: 4, recent_movements: [] }),
  "/dashboard/requests": () => ({ series: [], by_status: {}, open_total: 34, closed_total: 126, open_by_priority: { routine: 10, urgent: 12, critical: 12 }, awaiting_coordination: [], recent_emergencies: [] }),
  "/dashboard/activity": () => [],
  "/dashboard/cities": () => [],
};

function donor(i: number): DonorListItem {
  return {
    id: i,
    code: `DNR-${String(i).padStart(6, "0")}`,
    display_name: `Donor ${i}`,
    blood_group: "B+",
    city: "Lahore",
    locality: null,
    availability_status: "available",
    availability_confirmed_at: new Date().toISOString(),
    consent_status: "granted",
    verification_status: "unverified",
    last_donation_date: null,
    registered_at: new Date().toISOString(),
    provenance: "synthetic",
    is_active: true,
    currently_available: true,
  };
}

afterEach(() => vi.unstubAllGlobals());

describe("dashboard", () => {
  it("renders KPI values from the API and low-stock alerts", async () => {
    mockFetch(dashboardHandlers);
    renderApp("/");
    expect(await screen.findByText("796")).toBeInTheDocument();
    expect(screen.getByText("Usable blood units")).toBeInTheDocument();
    expect(await screen.findByText(/1 blood group below the low-stock threshold/)).toBeInTheDocument();
    expect(screen.getByText("No requests are waiting for coordination.")).toBeInTheDocument();
  });

  it("shows an error state with retry when the summary fails", async () => {
    mockFetch({ ...dashboardHandlers, "/dashboard/summary": () => json({ detail: "Database unavailable" }, 500) });
    renderApp("/");
    expect(await screen.findByText("Database unavailable")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });

  it("sends filters to the API when they change", async () => {
    const calls = mockFetch(dashboardHandlers);
    renderApp("/");
    await screen.findByText("796");
    await userEvent.selectOptions(screen.getByLabelText("Blood group"), "O-");
    await waitFor(() =>
      expect(calls.some((c) => c.url.pathname.endsWith("/dashboard/summary") && c.url.searchParams.get("blood_group") === "O-")).toBe(true),
    );
  });
});

describe("donors", () => {
  it("lists donors with synthetic labels and paginates", async () => {
    const calls = mockFetch({
      "/auth/me": () => coordinator,
      "/meta/data-status": () => ({ demo_mode: true }),
      "/donors/cities": () => ["Lahore"],
      "/donors": (url) => {
        const page = Number(url.searchParams.get("page"));
        return { items: Array.from({ length: 25 }, (_, i) => donor((page - 1) * 25 + i + 1)), total: 60, page, page_size: 25 };
      },
    });
    renderApp("/donors");
    expect(await screen.findByText("Donor 1")).toBeInTheDocument();
    expect(screen.getAllByText("SYNTHETIC DEMO").length).toBeGreaterThan(0);
    expect(screen.getByText("1–25 of 60")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Next page" }));
    expect(await screen.findByText("Donor 26")).toBeInTheDocument();
    expect(calls.some((c) => c.url.searchParams.get("page") === "2")).toBe(true);
  });

  it("shows an empty state when no donors match", async () => {
    mockFetch({
      "/auth/me": () => coordinator,
      "/meta/data-status": () => ({ demo_mode: false }),
      "/donors/cities": () => [],
      "/donors": () => ({ items: [], total: 0, page: 1, page_size: 25 }),
    });
    renderApp("/donors?blood_group=AB-");
    expect(await screen.findByText("No donors match these filters")).toBeInTheDocument();
  });

  it("validates the registration form before submitting", async () => {
    const calls = mockFetch({ "/auth/me": () => coordinator, "/meta/data-status": () => ({ demo_mode: false }) });
    renderApp("/donors/new");
    await userEvent.click(await screen.findByRole("button", { name: "Register donor" }));
    expect(await screen.findByText("Name must be at least 2 characters")).toBeInTheDocument();
    expect(screen.getByText("Select a blood group")).toBeInTheDocument();
    expect(screen.getByText("Donor consent is required before registration")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "POST")).toBe(false);
  });

  it("submits a valid registration and shows server errors", async () => {
    const calls = mockFetch({
      "/auth/me": () => coordinator,
      "/meta/data-status": () => ({ demo_mode: false }),
      "POST /donors": () => json({ detail: [{ loc: ["body", "phone"], msg: "Enter a valid phone number" }] }, 422),
    });
    renderApp("/donors/new");
    await userEvent.type(await screen.findByLabelText("Display name"), "Sana Malik");
    await userEvent.selectOptions(screen.getByLabelText("Blood group"), "O-");
    await userEvent.type(screen.getByLabelText("City"), "Islamabad");
    await userEvent.type(screen.getByLabelText("Phone"), "+92-000-1234567");
    await userEvent.click(screen.getByRole("checkbox", { name: /consented/ }));
    await userEvent.click(screen.getByRole("button", { name: "Register donor" }));
    const alert = await screen.findByText(/phone: Enter a valid phone number/);
    expect(alert).toBeInTheDocument();
    const post = calls.find((c) => c.method === "POST");
    expect(post?.body).toMatchObject({ display_name: "Sana Malik", blood_group: "O-", consent_confirmed: true, email: null });
  });

  it("hides write actions from roles without donor write permission", async () => {
    mockFetch({
      "/auth/me": () => makeSession("admin", ["dashboard:view", "donors:read"]),
      "/meta/data-status": () => ({ demo_mode: true }),
      "/donors/cities": () => [],
      "/donors": () => ({ items: [donor(1)], total: 1, page: 1, page_size: 25 }),
    });
    renderApp("/donors");
    await screen.findByText("Donor 1");
    expect(screen.queryByRole("button", { name: /Register donor/ })).not.toBeInTheDocument();
    expect(screen.queryByText("Export CSV")).not.toBeInTheDocument();
    const table = screen.getByRole("table");
    expect(within(table).queryByText("+92-000")).not.toBeInTheDocument();
  });
});
