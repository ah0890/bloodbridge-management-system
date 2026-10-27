import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { ProvenanceBadge, StatusBadge } from "@/components/ui/badge";
import { Card, CardBody, CardHeader, PageHeader } from "@/components/ui/card";
import { Select } from "@/components/ui/form";
import { Alert, EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { api } from "@/lib/api";
import type { BloodBank } from "@/lib/domain";
import { useUrlState } from "@/lib/useUrlState";
import { fmtDate, fmtDateTime, humanize } from "@/lib/utils";

export function BloodBanksPage() {
  const { values, set } = useUrlState(["city"] as const);
  const banks = useQuery({ queryKey: ["banks", "all", values.city], queryFn: () => api.get<BloodBank[]>("/blood-banks", { city: values.city || undefined }) });
  const cities = useQuery({ queryKey: ["bank-cities"], queryFn: () => api.get<string[]>("/blood-banks/cities") });
  return (
    <>
      <PageHeader
        title="Blood banks & hospitals"
        description="Participating organisations, their verification status and data source. Registration, review and approval workflows arrive in a later milestone."
      />
      <Card>
        <div className="border-b border-border p-3 sm:max-w-xs">
          <Select id="bank-city" label="City" placeholder="All cities" options={cities.data ?? []} format={(c) => c} value={values.city} onChange={(e) => set({ city: e.target.value })} />
        </div>
        {banks.isError ? (
          <ErrorState error={banks.error} onRetry={() => banks.refetch()} />
        ) : banks.isLoading ? (
          <LoadingState />
        ) : !banks.data?.length ? (
          <EmptyState title="No organisations found" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[820px]">
              <thead className="border-b border-border bg-canvas/60">
                <tr>
                  <th className="th">Organisation</th>
                  <th className="th">Type</th>
                  <th className="th">City</th>
                  <th className="th">Verification</th>
                  <th className="th">Inventory updated</th>
                  <th className="th">Source</th>
                </tr>
              </thead>
              <tbody>
                {banks.data.map((b) => (
                  <tr key={b.id} className="border-b border-border last:border-0">
                    <td className="td">
                      <Link to={`/blood-banks/${b.id}`} className="font-medium text-ink hover:text-primary">
                        {b.name}
                      </Link>
                      <p className="font-mono text-2xs text-ink-subtle">{b.code}</p>
                    </td>
                    <td className="td">{humanize(b.org_type)}</td>
                    <td className="td">{b.city}</td>
                    <td className="td">
                      <StatusBadge status={b.verification_status} />
                      {!b.is_active && <p className="text-2xs text-ink-subtle">Inactive</p>}
                    </td>
                    <td className="td text-ink-muted">{b.supported_components.length ? fmtDateTime(b.inventory_updated_at) : "Holds no inventory"}</td>
                    <td className="td">
                      <ProvenanceBadge provenance={b.provenance} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}

export function BloodBankDetailPage() {
  const { id } = useParams();
  const bank = useQuery({ queryKey: ["bank", id], queryFn: () => api.get<BloodBank>(`/blood-banks/${id}`) });
  if (bank.isLoading) return <LoadingState />;
  if (bank.isError || !bank.data) return <ErrorState error={bank.error} />;
  const b = bank.data;
  return (
    <>
      <PageHeader title={b.name} description={<span className="flex items-center gap-2"><span className="font-mono">{b.code}</span><ProvenanceBadge provenance={b.provenance} /></span>} />
      {b.provenance === "synthetic" && (
        <Alert tone="demo" className="mb-4" title="Fictional organisation">
          This organisation was generated for demonstration. It is not a real facility and its address and contact details are fictional.
        </Alert>
      )}
      <Card className="max-w-3xl">
        <CardHeader title="Organisation details" />
        <CardBody>
          <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
            {[
              ["Type", humanize(b.org_type)],
              ["City", b.city],
              ["Address", b.address ?? "—"],
              ["Phone", b.phone ?? "—"],
              ["Email", b.email ?? "—"],
              ["Operating hours", b.operating_hours ?? "Not verified"],
              ["Supported components", b.supported_components.length ? b.supported_components.map(humanize).join(", ") : "None (requesting facility)"],
              ["Verification", <StatusBadge key="v" status={b.verification_status} />],
              ["Last verified", fmtDate(b.last_verified_at)],
              ["Inventory updated", fmtDateTime(b.inventory_updated_at)],
              ["Data source", b.source_reference ?? "—"],
              ["Status", b.is_active ? "Active" : "Inactive"],
            ].map(([k, v]) => (
              <div key={k as string}>
                <dt className="text-xs text-ink-subtle">{k}</dt>
                <dd className="mt-0.5 break-words">{v}</dd>
              </div>
            ))}
          </dl>
        </CardBody>
      </Card>
    </>
  );
}
