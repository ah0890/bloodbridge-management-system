import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ProvenanceBadge } from "@/components/ui/badge";
import { Card, CardHeader, PageHeader } from "@/components/ui/card";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { api } from "@/lib/api";
import type { Provenance } from "@/lib/types";

interface Hit {
  id: number;
  code: string;
  label: string;
  meta: string;
  provenance: Provenance;
}
type Results = Record<"donors" | "requests" | "blood_banks", Hit[]>;

const SECTIONS: { key: keyof Results; title: string; href: (id: number) => string }[] = [
  { key: "requests", title: "Blood requests", href: (id) => `/requests/${id}` },
  { key: "donors", title: "Donors", href: (id) => `/donors/${id}` },
  { key: "blood_banks", title: "Blood banks", href: (id) => `/blood-banks/${id}` },
];

export function SearchPage() {
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const [term, setTerm] = useState(q);
  useEffect(() => setTerm(q), [q]);
  const results = useQuery({ queryKey: ["search", q], queryFn: () => api.get<Results>("/search", { q }), enabled: q.trim().length >= 2 });
  const total = results.data ? SECTIONS.reduce((n, s) => n + results.data[s.key].length, 0) : 0;

  return (
    <>
      <PageHeader title="Search" description="Search the records your role can access. Results never include contact details." />
      <form
        role="search"
        className="mb-5 max-w-xl"
        onSubmit={(e) => {
          e.preventDefault();
          setParams(term.trim() ? { q: term.trim() } : {});
        }}
      >
        <label htmlFor="search-page-q" className="sr-only">
          Search
        </label>
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-ink-subtle" aria-hidden />
          <input id="search-page-q" autoFocus className="input h-10 pl-9" placeholder="Request ID, donor ID, name, hospital or city" value={term} onChange={(e) => setTerm(e.target.value)} />
        </div>
      </form>
      {q.trim().length < 2 ? (
        <EmptyState title="Enter at least two characters" />
      ) : results.isLoading ? (
        <LoadingState />
      ) : results.isError ? (
        <ErrorState error={results.error} />
      ) : total === 0 ? (
        <EmptyState title={`No results for “${q}”`} />
      ) : (
        <div className="grid gap-5 lg:grid-cols-3">
          {SECTIONS.filter((s) => results.data![s.key].length).map((s) => (
            <Card key={s.key}>
              <CardHeader title={s.title} />
              <ul className="divide-y divide-border">
                {results.data![s.key].map((h) => (
                  <li key={h.id}>
                    <Link to={s.href(h.id)} className="block px-4 py-2.5 hover:bg-canvas">
                      <p className="flex items-center justify-between gap-2 text-sm font-medium text-ink">
                        <span className="truncate">{h.label}</span>
                        {h.provenance === "synthetic" && <ProvenanceBadge provenance={h.provenance} />}
                      </p>
                      <p className="truncate text-xs text-ink-subtle">
                        <span className="font-mono">{h.code}</span> · {h.meta}
                      </p>
                    </Link>
                  </li>
                ))}
              </ul>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
