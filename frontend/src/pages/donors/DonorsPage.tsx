import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Download, Plus, Search, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { BloodGroupBadge, ProvenanceBadge, StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, PageHeader } from "@/components/ui/card";
import { Pagination, Select } from "@/components/ui/form";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { api, downloadUrl } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { AVAILABILITY, VERIFICATION, type DonorListItem } from "@/lib/domain";
import { BLOOD_GROUPS, type Page } from "@/lib/types";
import { useUrlState } from "@/lib/useUrlState";
import { cn, fmtDate, fmtNumber, fmtRelative } from "@/lib/utils";

const KEYS = ["q", "blood_group", "city", "availability", "consent", "verification", "currently_available", "active", "page"] as const;
const PAGE_SIZE = 25;

export function DonorsPage() {
  const { can } = useAuth();
  const navigate = useNavigate();
  const { values, set, clear } = useUrlState(KEYS);
  const [term, setTerm] = useState(values.q);
  useEffect(() => setTerm(values.q), [values.q]);

  // Debounce free-text search into the URL.
  useEffect(() => {
    const t = setTimeout(() => term !== values.q && set({ q: term }), 300);
    return () => clearTimeout(t);
  }, [term, values.q, set]);

  const page = Number(values.page) || 1;
  const params = {
    q: values.q || undefined,
    blood_group: values.blood_group || undefined,
    city: values.city || undefined,
    availability: values.availability || undefined,
    consent: values.consent || undefined,
    verification: values.verification || undefined,
    currently_available: values.currently_available || undefined,
    active: values.active || "true",
    page,
    page_size: PAGE_SIZE,
  };
  const list = useQuery({
    queryKey: ["donors", params],
    queryFn: () => api.get<Page<DonorListItem>>("/donors", params),
    placeholderData: keepPreviousData,
  });
  const cities = useQuery({ queryKey: ["donor-cities"], queryFn: () => api.get<string[]>("/donors/cities"), staleTime: 10 * 60_000 });
  const filtered = KEYS.some((k) => k !== "page" && values[k]);

  return (
    <>
      <PageHeader
        title="Donors"
        description="Registered donors and their consent, availability and verification. Registration is not medical eligibility — screening happens at the blood bank."
        actions={
          <>
            {can("donors:export") && (
              <Button variant="secondary" asChild>
                <a
                  href={downloadUrl("/donors/export.csv", {
                    blood_group: params.blood_group,
                    city: params.city,
                    availability: params.availability,
                  })}
                >
                  <Download /> Export CSV
                </a>
              </Button>
            )}
            {can("donors:write") && (
              <Button onClick={() => navigate("/donors/new")}>
                <Plus /> Register donor
              </Button>
            )}
          </>
        }
      />

      <Card>
        <div className="grid grid-cols-2 gap-3 border-b border-border p-3 md:grid-cols-4 xl:grid-cols-8">
          <div className="col-span-2 md:col-span-4 xl:col-span-2">
            <label htmlFor="donor-q" className="field-label">
              Search
            </label>
            <div className="relative">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-ink-subtle" aria-hidden />
              <input id="donor-q" className="input pl-8" placeholder="Donor ID, name or city" value={term} onChange={(e) => setTerm(e.target.value)} />
            </div>
          </div>
          <Select id="d-group" label="Blood group" placeholder="All" options={BLOOD_GROUPS} format={(g) => g} value={values.blood_group} onChange={(e) => set({ blood_group: e.target.value })} />
          <Select id="d-city" label="City" placeholder="All" options={cities.data ?? []} format={(c) => c} value={values.city} onChange={(e) => set({ city: e.target.value })} />
          <Select id="d-avail" label="Availability" placeholder="Any" options={AVAILABILITY} value={values.availability} onChange={(e) => set({ availability: e.target.value })} />
          <Select id="d-consent" label="Consent" placeholder="Any" options={["granted", "withdrawn"]} value={values.consent} onChange={(e) => set({ consent: e.target.value })} />
          <Select id="d-verif" label="Verification" placeholder="Any" options={VERIFICATION} value={values.verification} onChange={(e) => set({ verification: e.target.value })} />
          <Select
            id="d-active"
            label="Record status"
            options={[
              { value: "", label: "Active" },
              { value: "false", label: "Inactive" },
              { value: "all", label: "All" },
            ]}
            value={values.active}
            onChange={(e) => set({ active: e.target.value })}
          />
        </div>
        <div className="flex flex-wrap items-center gap-2 border-b border-border px-3 py-2 text-xs">
          <label className="inline-flex cursor-pointer items-center gap-2 text-ink-muted">
            <input
              type="checkbox"
              className="size-4 rounded border-border accent-[rgb(var(--primary))]"
              checked={values.currently_available === "true"}
              onChange={(e) => set({ currently_available: e.target.checked ? "true" : "" })}
            />
            Currently available only (consent, recent confirmation, past donation interval)
          </label>
          <span className="ml-auto text-ink-subtle">{list.data ? `${fmtNumber(list.data.total)} donors` : ""}</span>
          {filtered && (
            <Button variant="ghost" size="sm" onClick={clear}>
              <X /> Clear
            </Button>
          )}
        </div>

        {list.isError ? (
          <ErrorState error={list.error} onRetry={() => list.refetch()} />
        ) : list.isLoading ? (
          <LoadingState />
        ) : !list.data?.items.length ? (
          <EmptyState title="No donors match these filters" description="Adjust or clear the filters to see more records." />
        ) : (
          <>
            <div className={cn("overflow-x-auto", list.isFetching && "opacity-70")}>
              <table className="w-full min-w-[860px]">
                <thead className="border-b border-border bg-canvas/60">
                  <tr>
                    <th className="th">Donor</th>
                    <th className="th">Group</th>
                    <th className="th">City</th>
                    <th className="th">Availability</th>
                    <th className="th">Consent</th>
                    <th className="th">Verification</th>
                    <th className="th">Last donation</th>
                    <th className="th">Source</th>
                  </tr>
                </thead>
                <tbody>
                  {list.data.items.map((d) => (
                    <tr key={d.id} className="cursor-pointer border-b border-border last:border-0 hover:bg-canvas" onClick={() => navigate(`/donors/${d.id}`)}>
                      <td className="td">
                        <Link to={`/donors/${d.id}`} className="font-medium text-ink hover:text-primary" onClick={(e) => e.stopPropagation()}>
                          {d.display_name}
                        </Link>
                        <p className="font-mono text-2xs text-ink-subtle">{d.code}</p>
                      </td>
                      <td className="td">
                        <BloodGroupBadge group={d.blood_group} />
                      </td>
                      <td className="td">
                        {d.city}
                        {d.locality && <p className="text-2xs text-ink-subtle">{d.locality}</p>}
                      </td>
                      <td className="td">
                        <StatusBadge status={d.availability_status} />
                        <p className="mt-0.5 text-2xs text-ink-subtle">
                          {d.currently_available ? "Current" : d.availability_confirmed_at ? `Confirmed ${fmtRelative(d.availability_confirmed_at)}` : "Never confirmed"}
                        </p>
                      </td>
                      <td className="td">
                        <StatusBadge status={d.consent_status} />
                      </td>
                      <td className="td">
                        <StatusBadge status={d.verification_status} />
                      </td>
                      <td className="td text-ink-muted">{fmtDate(d.last_donation_date)}</td>
                      <td className="td">
                        <ProvenanceBadge provenance={d.provenance} />
                        {!d.is_active && <p className="mt-0.5 text-2xs text-ink-subtle">Inactive</p>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={page} pageSize={PAGE_SIZE} total={list.data.total} onPage={(p) => set({ page: String(p) }, false)} />
          </>
        )}
      </Card>
    </>
  );
}
