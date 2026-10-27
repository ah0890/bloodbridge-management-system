import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight, Info } from "lucide-react";
import { Link } from "react-router-dom";
import { BloodGroupBadge, ProvenanceBadge, StatusBadge } from "@/components/ui/badge";
import { Card, CardBody, CardHeader, PageHeader } from "@/components/ui/card";
import { Alert, EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useUrlState } from "@/lib/useUrlState";
import { cn, fmtDate, fmtDateTime, fmtNumber, fmtRelative, humanize } from "@/lib/utils";
import { BLOOD_GROUPS } from "@/lib/types";
import { PriorityBars, RequestsTrendChart, StockByGroupChart } from "./Charts";
import { DashboardFilters, FILTER_KEYS } from "./DashboardFilters";
import { KpiGrid } from "./KpiGrid";
import type { ActivityEvent, CityRow, InventoryHealth, RequestActivity, RequestBrief, Summary } from "./types";

export function DashboardPage() {
  const { session } = useAuth();
  const { values, set, clear } = useUrlState(FILTER_KEYS);
  const q = Object.fromEntries(Object.entries(values).filter(([, v]) => v));
  const key = (name: string) => ["dashboard", name, q];

  const summary = useQuery({ queryKey: key("summary"), queryFn: () => api.get<Summary>("/dashboard/summary", q) });
  const health = useQuery({ queryKey: key("health"), queryFn: () => api.get<InventoryHealth>("/dashboard/inventory-health", q) });
  const requests = useQuery({ queryKey: key("requests"), queryFn: () => api.get<RequestActivity>("/dashboard/requests", q) });
  const activity = useQuery({ queryKey: key("activity"), queryFn: () => api.get<ActivityEvent[]>("/dashboard/activity", { ...q, limit: 20 }) });
  const cities = useQuery({ queryKey: key("cities"), queryFn: () => api.get<CityRow[]>("/dashboard/cities", q) });

  const firstName = session?.user.full_name.split(" ")[0] ?? "";
  const scoped = summary.data?.scope.org_scoped;

  return (
    <>
      <PageHeader
        title="Operations overview"
        description={
          scoped
            ? `Figures for ${session?.user.blood_bank?.name}. Values are computed live from the database.`
            : `Welcome back${firstName ? `, ${firstName}` : ""}. Values are computed live from the database; hover a card for its exact definition.`
        }
      />
      <DashboardFilters values={values} onChange={(p) => set(p)} onClear={clear} />

      {summary.isError ? (
        <Card>
          <ErrorState error={summary.error} onRetry={() => summary.refetch()} />
        </Card>
      ) : (
        <KpiGrid summary={summary.data} loading={summary.isLoading} />
      )}

      <div className="mt-5 grid gap-5 xl:grid-cols-5">
        <Card className="xl:col-span-3">
          <CardHeader
            title="Usable stock by blood group"
            description="Units · available, screening-passed, in date. Quarantined, reserved, expired and issued stock excluded."
          />
          <CardBody>
            {summary.data ? (
              <StockByGroupChart data={summary.data.stock_by_group} threshold={summary.data.thresholds.low_stock_units} />
            ) : (
              <LoadingState />
            )}
          </CardBody>
        </Card>
        <InventoryHealthCard query={health} />
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-5">
        <Card className="xl:col-span-3">
          <CardHeader title="Requests over time" description="Per day · received (submitted) vs fulfilled (closed as fulfilled)" />
          <CardBody>
            {requests.isError ? (
              <ErrorState error={requests.error} onRetry={() => requests.refetch()} />
            ) : requests.data ? (
              <RequestsTrendChart series={requests.data.series} />
            ) : (
              <LoadingState />
            )}
          </CardBody>
        </Card>
        <Card className="xl:col-span-2">
          <CardHeader title="Open requests by priority" description="Operational priority set by staff — not medical triage" />
          <CardBody>
            {requests.data ? (
              <>
                <PriorityBars data={requests.data.open_by_priority} />
                <dl className="mt-5 grid grid-cols-2 gap-3 border-t border-border pt-4 text-center">
                  <div>
                    <dt className="text-xs text-ink-muted">Open</dt>
                    <dd className="text-xl font-semibold tabular-nums">{fmtNumber(requests.data.open_total)}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-ink-muted">Closed (all outcomes)</dt>
                    <dd className="text-xl font-semibold tabular-nums">{fmtNumber(requests.data.closed_total)}</dd>
                  </div>
                </dl>
              </>
            ) : (
              <LoadingState />
            )}
          </CardBody>
        </Card>
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <RequestListCard
          title="Awaiting coordination"
          description="Submitted, under review or with matches to contact · soonest required-by first"
          rows={requests.data?.awaiting_coordination}
          loading={requests.isLoading}
          empty="No requests are waiting for coordination."
        />
        <RequestListCard
          title="Recent critical requests"
          description="For life-threatening emergencies, the hospital and 1122 must be contacted directly."
          rows={requests.data?.recent_emergencies}
          loading={requests.isLoading}
          empty="No critical requests match the current filters."
        />
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-5">
        <CityCard query={cities} />
        <ActivityCard query={activity} />
      </div>
    </>
  );
}

function InventoryHealthCard({ query }: { query: UseQueryResult<InventoryHealth> }) {
  const d = query.data;
  return (
    <Card className="xl:col-span-2">
      <CardHeader title="Inventory health" description="Low stock, expiry and stock excluded from usable totals" />
      <CardBody className="space-y-4">
        {query.isError ? (
          <ErrorState error={query.error} onRetry={() => query.refetch()} />
        ) : !d ? (
          <LoadingState />
        ) : (
          <>
            {d.low_stock.length ? (
              <Alert tone="warning" title={`${d.low_stock.length} blood group${d.low_stock.length > 1 ? "s" : ""} below the low-stock threshold`}>
                <span className="flex flex-wrap gap-1.5 pt-1">
                  {d.low_stock.map((l) => (
                    <span key={l.blood_group} className="inline-flex items-center gap-1">
                      <BloodGroupBadge group={l.blood_group} /> <span className="text-xs tabular-nums">{l.units} u</span>
                    </span>
                  ))}
                </span>
              </Alert>
            ) : (
              <Alert tone="success" title="All blood groups at or above the low-stock threshold" />
            )}
            <dl className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4 xl:grid-cols-2 2xl:grid-cols-4">
              {[
                ["Quarantined", d.excluded_units.quarantined ?? 0],
                ["Reserved", d.excluded_units.reserved ?? 0],
                ["Past expiry, not written off", d.excluded_units.expired_not_yet_written_off ?? 0],
                ["Expired/discarded (30 d)", d.wasted_last_30_days],
              ].map(([label, n]) => (
                <div key={label as string} className="rounded border border-border bg-canvas px-2.5 py-2">
                  <dt className="text-ink-subtle">{label}</dt>
                  <dd className="text-base font-semibold tabular-nums text-ink">{fmtNumber(n as number)}</dd>
                </div>
              ))}
            </dl>
            <div>
              <h3 className="mb-1.5 text-xs font-semibold text-ink-muted">Expiring soonest</h3>
              {d.expiring.length ? (
                <ul className="divide-y divide-border rounded border border-border">
                  {d.expiring.slice(0, 5).map((b) => (
                    <li key={b.id} className="flex items-center gap-2 px-2.5 py-1.5 text-xs">
                      <BloodGroupBadge group={b.blood_group} />
                      <span className="min-w-0 flex-1 truncate">
                        {b.quantity} × {humanize(b.component)} · <span className="text-ink-subtle">{b.blood_bank}</span>
                      </span>
                      <span className="shrink-0 font-medium text-warning">{fmtDate(b.expires_on)}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-ink-subtle">No usable stock expires within the warning window.</p>
              )}
            </div>
          </>
        )}
      </CardBody>
    </Card>
  );
}

function RequestListCard({ title, description, rows, loading, empty }: {
  title: string;
  description: string;
  rows?: RequestBrief[];
  loading: boolean;
  empty: string;
}) {
  return (
    <Card>
      <CardHeader title={title} description={description} actions={<Link to="/requests" className="text-xs font-medium text-primary hover:underline">All requests</Link>} />
      {loading ? (
        <LoadingState />
      ) : !rows?.length ? (
        <EmptyState title={empty} />
      ) : (
        <ul className="divide-y divide-border">
          {rows.map((r) => {
            const overdue = new Date(r.required_by).getTime() < Date.now();
            return (
              <li key={r.id}>
                <Link to={`/requests/${r.id}`} className="flex items-center gap-3 px-4 py-2.5 hover:bg-canvas">
                  <BloodGroupBadge group={r.blood_group} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-ink">
                      {r.code} · {r.units_fulfilled}/{r.units_required} × {humanize(r.component)}
                    </p>
                    <p className="truncate text-xs text-ink-subtle">
                      {r.city} · <span className={cn(overdue && "font-medium text-danger")}>{overdue ? "Overdue since " : "Needed by "}{fmtDateTime(r.required_by)}</span>
                    </p>
                  </div>
                  <div className="hidden shrink-0 flex-col items-end gap-1 sm:flex">
                    <StatusBadge status={r.priority} />
                    <StatusBadge status={r.status} />
                  </div>
                  <ArrowRight className="size-4 shrink-0 text-ink-subtle" aria-hidden />
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}

function CityCard({ query }: { query: UseQueryResult<CityRow[]> }) {
  return (
    <Card className="xl:col-span-3">
      <CardHeader
        title="City-level availability"
        description="Usable units by blood group, open requests and currently available donors (aggregate counts only)"
        actions={<Link to="/geography" className="text-xs font-medium text-primary hover:underline">Details</Link>}
      />
      {query.isError ? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      ) : !query.data ? (
        <LoadingState />
      ) : !query.data.length ? (
        <EmptyState title="No city data" />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px]">
            <thead className="border-b border-border bg-canvas/60">
              <tr>
                <th className="th">City</th>
                <th className="th text-right">Banks</th>
                {BLOOD_GROUPS.map((g) => (
                  <th key={g} className="th text-right font-mono">
                    {g}
                  </th>
                ))}
                <th className="th text-right">Total</th>
                <th className="th text-right">Open req.</th>
                <th className="th text-right">Donors</th>
              </tr>
            </thead>
            <tbody>
              {query.data.map((c) => (
                <tr key={c.city} className="border-b border-border last:border-0">
                  <td className="td font-medium">
                    <span className="flex items-center gap-1.5">
                      {c.city}
                      {c.coverage_gap && <AlertTriangle className="size-3.5 text-warning" aria-label="Coverage gap" />}
                    </span>
                  </td>
                  <td className="td text-right tabular-nums">{c.verified_banks}</td>
                  {BLOOD_GROUPS.map((g) => (
                    <td key={g} className={cn("td text-right tabular-nums", (c.stock_by_group[g] ?? 0) === 0 && "text-ink-subtle")}>
                      {c.stock_by_group[g] ?? 0}
                    </td>
                  ))}
                  <td className="td text-right font-semibold tabular-nums">{fmtNumber(c.available_units)}</td>
                  <td className={cn("td text-right tabular-nums", c.open_requests > 0 && "font-semibold text-blood")}>{c.open_requests}</td>
                  <td className="td text-right tabular-nums">{fmtNumber(c.available_donors)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="flex items-center gap-1.5 border-t border-border px-4 py-2 text-2xs text-ink-subtle">
            <AlertTriangle className="size-3 text-warning" aria-hidden /> Coverage gap: no verified organisation, or open requests with no usable stock in the city.
          </p>
        </div>
      )}
    </Card>
  );
}

function ActivityCard({ query }: { query: UseQueryResult<ActivityEvent[]> }) {
  return (
    <Card className="xl:col-span-2">
      <CardHeader title="Recent activity" description="From request, inventory, donor and verification records" />
      {query.isError ? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      ) : !query.data ? (
        <LoadingState />
      ) : !query.data.length ? (
        <EmptyState title="No recent activity" />
      ) : (
        <ol className="max-h-[28rem] divide-y divide-border overflow-y-auto">
          {query.data.map((e, i) => (
            <li key={`${e.at}-${i}`}>
              <Link to={e.link} className="flex gap-3 px-4 py-2.5 hover:bg-canvas">
                <span className={cn("mt-1.5 size-2 shrink-0 rounded-full", e.kind.startsWith("stock") ? "bg-[var(--chart-1)]" : e.kind.startsWith("request") ? "bg-blood" : e.kind === "bank_verified" ? "bg-success" : "bg-[var(--chart-3)]")} aria-hidden />
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-ink">{e.text}</p>
                  <p className="mt-0.5 flex items-center gap-2 text-xs text-ink-subtle">
                    <time dateTime={e.at} title={fmtDateTime(e.at)}>
                      {fmtRelative(e.at)}
                    </time>
                    {e.provenance === "synthetic" && <ProvenanceBadge provenance={e.provenance} />}
                  </p>
                </div>
              </Link>
            </li>
          ))}
        </ol>
      )}
      <p className="flex items-center gap-1.5 border-t border-border px-4 py-2 text-2xs text-ink-subtle">
        <Info className="size-3" aria-hidden /> Donors are referenced by ID only.
      </p>
    </Card>
  );
}
