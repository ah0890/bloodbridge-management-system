import { AlertTriangle, Building2, CheckCircle2, ClipboardList, Droplets, Hourglass, UserCheck, Users, type LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";
import { cn, fmtDate, fmtNumber } from "@/lib/utils";
import type { Summary } from "./types";

interface Kpi {
  key: keyof Summary["kpis"];
  label: string;
  icon: LucideIcon;
  definition: string;
  tone?: "blood" | "warning";
  to?: string;
}

function kpiList(t: Summary["thresholds"]): Kpi[] {
  return [
    { key: "registered_donors", label: "Registered donors", icon: Users, definition: "Active donor records (excludes deactivated and anonymised).", to: "/donors" },
    {
      key: "available_donors",
      label: "Currently available donors",
      icon: UserCheck,
      definition: `Consent granted, availability confirmed in the last ${t.availability_fresh_days} days, and no donation in the last ${t.whole_blood_deferral_days} days. Not a medical eligibility decision.`,
      to: "/donors?currently_available=true",
    },
    {
      key: "available_units",
      label: "Usable blood units",
      icon: Droplets,
      definition: "Units that are available, screening-passed and in date at active organisations. Quarantined, reserved, expired and issued stock is excluded.",
      to: "/inventory",
    },
    { key: "active_requests", label: "Active requests", icon: ClipboardList, definition: "Requests not yet fulfilled, cancelled or closed.", to: "/requests" },
    {
      key: "critical_or_overdue_requests",
      label: "Critical or overdue",
      icon: AlertTriangle,
      tone: "blood",
      definition: "Active requests with critical operational priority, or whose required-by time has passed.",
      to: "/requests?priority=critical",
    },
    { key: "verified_blood_banks", label: "Verified organisations", icon: Building2, definition: "Active organisations with verified status.", to: "/blood-banks" },
    {
      key: "expiring_units",
      label: `Expiring ≤ ${t.expiry_warning_days} days`,
      icon: Hourglass,
      tone: "warning",
      definition: `Usable units whose expiry date falls within the next ${t.expiry_warning_days} days.`,
      to: "/inventory?expiring=true",
    },
    { key: "fulfilled_in_period", label: "Fulfilled in period", icon: CheckCircle2, definition: "Requests marked fulfilled with a close date inside the selected period." },
  ];
}

export function KpiGrid({ summary, loading }: { summary?: Summary; loading: boolean }) {
  const t = summary?.thresholds ?? { low_stock_units: 10, expiry_warning_days: 7, availability_fresh_days: 90, whole_blood_deferral_days: 90 };
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      {kpiList(t).map((k) => {
        const value = summary?.kpis[k.key];
        const body = (
          <>
            <div className="flex items-start justify-between gap-2">
              <p className="text-xs font-medium text-ink-muted">{k.label}</p>
              <k.icon className={cn("size-4 shrink-0 text-ink-subtle", k.tone === "blood" && "text-blood", k.tone === "warning" && "text-warning")} aria-hidden />
            </div>
            <p className={cn("mt-2 text-2xl font-semibold tabular-nums tracking-tight text-ink", loading && "animate-pulse text-ink-subtle")}>
              {loading ? "—" : fmtNumber(value as number)}
            </p>
            <p className="mt-1 line-clamp-2 text-2xs text-ink-subtle">
              {k.key === "fulfilled_in_period" && summary
                ? `${fmtDate(summary.kpis.period_start)} – ${fmtDate(summary.kpis.period_end)}`
                : k.definition}
            </p>
          </>
        );
        return k.to ? (
          <Link key={k.key} to={k.to} title={k.definition} className="card block p-3.5 transition-colors hover:border-primary/40">
            {body}
          </Link>
        ) : (
          <div key={k.key} title={k.definition} className="card p-3.5">
            {body}
          </div>
        );
      })}
    </div>
  );
}
