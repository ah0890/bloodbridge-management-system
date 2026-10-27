import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

/** Filter state kept in the URL so views are shareable and survive refresh. */
export function useUrlState<K extends string>(keys: readonly K[]) {
  const [params, setParams] = useSearchParams();
  const values = useMemo(() => {
    const out = {} as Record<K, string>;
    for (const k of keys) out[k] = params.get(k) ?? "";
    return out;
  }, [params]);

  const set = useCallback(
    (patch: Partial<Record<K, string>>, resetPage = true) => {
      setParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          for (const [k, v] of Object.entries(patch) as [string, string | undefined][]) {
            if (v) next.set(k, v);
            else next.delete(k);
          }
          if (resetPage && !("page" in patch)) next.delete("page");
          return next;
        },
        { replace: true },
      );
    },
    [setParams],
  );

  const clear = useCallback(() => setParams(new URLSearchParams(), { replace: true }), [setParams]);
  return { values, set, clear };
}
