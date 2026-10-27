import { useQuery } from "@tanstack/react-query";
import { FlaskConical } from "lucide-react";
import { api } from "@/lib/api";

export interface DataStatus {
  synthetic_records: number;
  imported_records: number;
  verified_records: number;
  demo_mode: boolean;
}

export function useDataStatus() {
  return useQuery({ queryKey: ["meta", "data-status"], queryFn: () => api.get<DataStatus>("/meta/data-status"), staleTime: 5 * 60_000 });
}

/** Persistent notice whenever synthetic records exist in the database. */
export function DemoBanner() {
  const { data } = useDataStatus();
  if (!data?.demo_mode) return null;
  return (
    <div className="flex items-start gap-2 border-b border-demo/20 bg-demo-soft px-4 py-1.5 text-xs text-demo sm:items-center sm:px-6">
      <FlaskConical className="mt-0.5 size-3.5 shrink-0 sm:mt-0" aria-hidden />
      <p>
        <strong className="font-semibold">SYNTHETIC DEMO DATA.</strong> Donors, organisations, inventory and requests shown here are
        generated for demonstration. They are not real people or facilities and no messages are ever sent to them.
      </p>
    </div>
  );
}
