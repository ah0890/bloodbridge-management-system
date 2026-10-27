import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Button } from "@/components/ui/button";
import { fmtNumber, humanize } from "@/lib/utils";
import { BLOOD_GROUPS, type BloodGroup } from "@/lib/types";
import type { Priority } from "@/lib/domain";

const C1 = "var(--chart-1)";
const C4 = "var(--chart-4)";
const GRID = "var(--chart-grid)";
const AXIS = { fontSize: 11, fill: "var(--chart-axis)" };

function TooltipBox({ title, rows }: { title: string; rows: { label: string; value: string; color?: string }[] }) {
  return (
    <div className="rounded border border-border bg-surface px-2.5 py-2 text-xs shadow-pop">
      <p className="mb-1 font-semibold text-ink">{title}</p>
      {rows.map((r) => (
        <p key={r.label} className="flex items-center gap-1.5 text-ink-muted">
          {r.color && <span className="inline-block size-2 rounded-full" style={{ background: r.color }} aria-hidden />}
          {r.label}: <span className="font-semibold tabular-nums text-ink">{r.value}</span>
        </p>
      ))}
    </div>
  );
}

/** Table alternative for every chart (accessibility and exact values). */
function ToggleTable({ children, table }: { children: React.ReactNode; table: React.ReactNode }) {
  const [asTable, setAsTable] = useState(false);
  return (
    <div>
      <div className="mb-1 flex justify-end">
        <Button variant="link" size="sm" className="text-xs" onClick={() => setAsTable((v) => !v)} aria-pressed={asTable}>
          {asTable ? "Show chart" : "Show table"}
        </Button>
      </div>
      {asTable ? <div className="overflow-x-auto">{table}</div> : children}
    </div>
  );
}

export function StockByGroupChart({ data, threshold }: { data: Record<BloodGroup, number>; threshold: number }) {
  const rows = BLOOD_GROUPS.map((g) => ({ group: g, units: data[g] ?? 0 }));
  return (
    <ToggleTable
      table={
        <table className="w-full">
          <thead>
            <tr className="border-b border-border">
              <th className="th">Blood group</th>
              <th className="th text-right">Usable units</th>
              <th className="th">Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.group} className="border-b border-border last:border-0">
                <td className="td font-mono font-semibold">{r.group}</td>
                <td className="td text-right tabular-nums">{fmtNumber(r.units)}</td>
                <td className="td text-xs">{r.units < threshold ? "Below low-stock threshold" : "OK"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      }
    >
      <div className="h-64" role="img" aria-label={`Usable units by blood group: ${rows.map((r) => `${r.group} ${r.units}`).join(", ")}`}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ top: 18, right: 8, bottom: 0, left: -12 }} barCategoryGap="22%">
            <CartesianGrid vertical={false} stroke={GRID} />
            <XAxis dataKey="group" tick={{ ...AXIS, fontWeight: 600 }} tickLine={false} axisLine={{ stroke: GRID }} />
            <YAxis tick={AXIS} tickLine={false} axisLine={false} allowDecimals={false} />
            <Tooltip
              cursor={{ fill: "rgb(15 23 42 / 0.04)" }}
              content={({ active, payload }) =>
                active && payload?.length ? (
                  <TooltipBox
                    title={`Group ${payload[0].payload.group}`}
                    rows={[
                      { label: "Usable units", value: fmtNumber(payload[0].payload.units) },
                      { label: "Low-stock threshold", value: String(threshold) },
                    ]}
                  />
                ) : null
              }
            />
            <ReferenceLine y={threshold} stroke="rgb(var(--warning))" strokeDasharray="4 3" label={{ value: `Low stock (${threshold})`, position: "insideBottomLeft", fontSize: 10, fill: "rgb(var(--warning))" }} />
            <Bar dataKey="units" fill={C1} radius={[4, 4, 0, 0]} maxBarSize={44} isAnimationActive={false}>
              <LabelList dataKey="units" position="top" style={{ fontSize: 11, fill: "rgb(var(--ink-muted))" }} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </ToggleTable>
  );
}

export function RequestsTrendChart({ series }: { series: { date: string; received: number; fulfilled: number }[] }) {
  const fmt = (d: string) => new Date(d + "T00:00:00").toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
  return (
    <ToggleTable
      table={
        <table className="w-full">
          <thead>
            <tr className="border-b border-border">
              <th className="th">Date</th>
              <th className="th text-right">Received</th>
              <th className="th text-right">Fulfilled</th>
            </tr>
          </thead>
          <tbody>
            {series.map((r) => (
              <tr key={r.date} className="border-b border-border last:border-0">
                <td className="td">{fmt(r.date)}</td>
                <td className="td text-right tabular-nums">{r.received}</td>
                <td className="td text-right tabular-nums">{r.fulfilled}</td>
              </tr>
            ))}
          </tbody>
        </table>
      }
    >
      <div className="h-64" role="img" aria-label="Requests received and fulfilled per day">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={series} margin={{ top: 8, right: 12, bottom: 0, left: -18 }}>
            <CartesianGrid vertical={false} stroke={GRID} />
            <XAxis dataKey="date" tickFormatter={fmt} tick={AXIS} tickLine={false} axisLine={{ stroke: GRID }} minTickGap={24} />
            <YAxis tick={AXIS} tickLine={false} axisLine={false} allowDecimals={false} />
            <Tooltip
              cursor={{ stroke: "var(--chart-axis)", strokeDasharray: "3 3" }}
              content={({ active, payload, label }) =>
                active && payload?.length ? (
                  <TooltipBox
                    title={fmt(String(label))}
                    rows={payload.map((p) => ({ label: humanize(String(p.dataKey)), value: String(p.value), color: String(p.color) }))}
                  />
                ) : null
              }
            />
            <Legend iconType="plainline" wrapperStyle={{ fontSize: 12, paddingTop: 4 }} formatter={(v) => <span className="text-ink-muted">{humanize(String(v))}</span>} />
            <Line isAnimationActive={false} type="monotone" dataKey="received" stroke={C1} strokeWidth={2} dot={false} activeDot={{ r: 4, strokeWidth: 2, stroke: "#fff" }} />
            <Line isAnimationActive={false} type="monotone" dataKey="fulfilled" stroke={C4} strokeWidth={2} dot={false} activeDot={{ r: 4, strokeWidth: 2, stroke: "#fff" }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </ToggleTable>
  );
}

const PRIORITY_STYLE: Record<Priority, string> = { routine: "bg-ink-subtle", urgent: "bg-warning", critical: "bg-blood" };

/** Status-coloured bars, always labelled — colour is never the only cue. */
export function PriorityBars({ data }: { data: Record<Priority, number> }) {
  const order: Priority[] = ["critical", "urgent", "routine"];
  const max = Math.max(1, ...order.map((p) => data[p] ?? 0));
  return (
    <ul className="space-y-2.5">
      {order.map((p) => (
        <li key={p} className="grid grid-cols-[4.5rem_1fr_2.5rem] items-center gap-2 text-xs">
          <span className="font-medium text-ink-muted">{humanize(p)}</span>
          <span className="h-2.5 rounded-full bg-canvas">
            <span className={`block h-full rounded-full ${PRIORITY_STYLE[p]}`} style={{ width: `${((data[p] ?? 0) / max) * 100}%` }} />
          </span>
          <span className="text-right font-semibold tabular-nums text-ink">{data[p] ?? 0}</span>
        </li>
      ))}
    </ul>
  );
}
