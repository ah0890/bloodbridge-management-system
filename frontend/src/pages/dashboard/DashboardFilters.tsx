import { useQuery } from "@tanstack/react-query";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/form";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { REQUEST_STATUSES, type BloodBank } from "@/lib/domain";
import { BLOOD_GROUPS } from "@/lib/types";

export const FILTER_KEYS = ["date_from", "date_to", "city", "blood_group", "blood_bank_id", "request_status"] as const;
export type FilterValues = Record<(typeof FILTER_KEYS)[number], string>;

export function DashboardFilters({
  values,
  onChange,
  onClear,
}: {
  values: FilterValues;
  onChange: (patch: Partial<FilterValues>) => void;
  onClear: () => void;
}) {
  const { session } = useAuth();
  const orgScoped = session?.user.role === "bank_manager";
  const cities = useQuery({ queryKey: ["bank-cities"], queryFn: () => api.get<string[]>("/blood-banks/cities"), staleTime: 10 * 60_000 });
  const banks = useQuery({
    queryKey: ["banks", values.city],
    queryFn: () => api.get<BloodBank[]>("/blood-banks", { city: values.city || undefined, active: true }),
    enabled: !orgScoped,
    staleTime: 10 * 60_000,
  });
  const active = FILTER_KEYS.some((k) => values[k]);

  return (
    <div className="card mb-5 grid grid-cols-2 gap-3 p-3 sm:grid-cols-3 lg:grid-cols-6 xl:flex xl:items-end" role="group" aria-label="Dashboard filters">
      <div className="min-w-0 xl:w-36">
        <label htmlFor="f-from" className="field-label">
          From
        </label>
        <input id="f-from" type="date" className="input" value={values.date_from} max={values.date_to || undefined} onChange={(e) => onChange({ date_from: e.target.value })} />
      </div>
      <div className="min-w-0 xl:w-36">
        <label htmlFor="f-to" className="field-label">
          To
        </label>
        <input id="f-to" type="date" className="input" value={values.date_to} min={values.date_from || undefined} onChange={(e) => onChange({ date_to: e.target.value })} />
      </div>
      <Select id="f-city" label="City" placeholder="All cities" options={cities.data ?? []} format={(c) => c} value={values.city} onChange={(e) => onChange({ city: e.target.value, blood_bank_id: "" })} className="xl:w-40" />
      <Select id="f-group" label="Blood group" placeholder="All groups" options={BLOOD_GROUPS} format={(g) => g} value={values.blood_group} onChange={(e) => onChange({ blood_group: e.target.value })} className="xl:w-32" />
      {orgScoped ? (
        <div className="min-w-0 xl:w-56">
          <span className="field-label">Blood bank</span>
          <p className="input flex items-center truncate bg-canvas text-ink-muted" title="Bank managers see their own organisation">
            {session?.user.blood_bank?.name}
          </p>
        </div>
      ) : (
        <Select
          id="f-bank"
          label="Blood bank"
          placeholder="All blood banks"
          options={(banks.data ?? []).filter((b) => b.supported_components.length).map((b) => ({ value: String(b.id), label: b.name }))}
          value={values.blood_bank_id}
          onChange={(e) => onChange({ blood_bank_id: e.target.value })}
          className="xl:w-56"
        />
      )}
      <Select id="f-status" label="Request status" placeholder="All statuses" options={REQUEST_STATUSES} value={values.request_status} onChange={(e) => onChange({ request_status: e.target.value })} className="xl:w-48" />
      <div className="col-span-2 flex items-end sm:col-span-1">
        <Button variant="ghost" size="sm" onClick={onClear} disabled={!active} className="h-9">
          <X /> Clear filters
        </Button>
      </div>
    </div>
  );
}
