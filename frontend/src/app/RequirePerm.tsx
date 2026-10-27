import { ShieldAlert } from "lucide-react";
import type { ReactNode } from "react";
import { EmptyState } from "@/components/ui/states";
import { useAuth } from "@/lib/auth";
import type { Permission } from "@/lib/types";

/** Route guard. UX only: every endpoint enforces the same permission on the server. */
export function RequirePerm({ perm, children }: { perm: Permission; children: ReactNode }) {
  const { can } = useAuth();
  if (!can(perm))
    return (
      <EmptyState
        icon={<ShieldAlert className="size-8" />}
        title="Access restricted"
        description="Your role does not have access to this page. Contact a platform administrator if you believe this is a mistake."
      />
    );
  return <>{children}</>;
}
