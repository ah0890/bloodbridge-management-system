import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";
import { cn, humanize } from "@/lib/utils";
import type { Provenance } from "@/lib/types";

const badgeVariants = cva("inline-flex items-center gap-1 rounded-sm px-1.5 py-0.5 text-2xs font-semibold whitespace-nowrap", {
  variants: {
    tone: {
      neutral: "bg-canvas text-ink-muted border border-border",
      success: "bg-success-soft text-success",
      warning: "bg-warning-soft text-warning",
      danger: "bg-danger-soft text-danger",
      info: "bg-info-soft text-info",
      blood: "bg-blood-soft text-blood",
      demo: "bg-demo-soft text-demo",
    },
  },
  defaultVariants: { tone: "neutral" },
});

export type Tone = NonNullable<VariantProps<typeof badgeVariants>["tone"]>;

export function Badge({ className, tone, ...props }: HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />;
}

/** Visible provenance marker. Synthetic records must always carry this. */
export function ProvenanceBadge({ provenance, className }: { provenance: Provenance; className?: string }) {
  if (provenance === "synthetic")
    return (
      <Badge tone="demo" className={className} title="Synthetic demonstration record — not a real person or facility">
        SYNTHETIC DEMO
      </Badge>
    );
  if (provenance === "verified")
    return (
      <Badge tone="success" className={className}>
        Verified
      </Badge>
    );
  return (
    <Badge tone="info" className={className}>
      Imported
    </Badge>
  );
}

export function BloodGroupBadge({ group, className }: { group: string; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex h-6 min-w-[2.25rem] items-center justify-center rounded-sm border border-blood/25 bg-blood-soft px-1.5 font-mono text-xs font-bold text-blood",
        className,
      )}
    >
      {group}
    </span>
  );
}

const STATUS_TONES: Record<string, Tone> = {
  // inventory
  available: "success",
  reserved: "info",
  issued: "neutral",
  quarantined: "warning",
  expired: "danger",
  discarded: "neutral",
  transferred: "neutral",
  // requests
  submitted: "info",
  under_review: "info",
  searching: "warning",
  matches_found: "warning",
  coordination_in_progress: "warning",
  partially_fulfilled: "warning",
  fulfilled: "success",
  cancelled: "neutral",
  closed_unfulfilled: "danger",
  // priority
  routine: "neutral",
  urgent: "warning",
  critical: "blood",
  // verification
  verified: "success",
  pending: "warning",
  rejected: "danger",
  suspended: "danger",
  unverified: "neutral",
  phone_confirmed: "info",
  screened: "success",
  // donor availability
  unavailable: "neutral",
  temporarily_deferred: "warning",
  unknown: "neutral",
  // consent
  granted: "success",
  withdrawn: "danger",
  // screening
  passed: "success",
  failed: "danger",
};

export function StatusBadge({ status, className }: { status: string; className?: string }) {
  return (
    <Badge tone={STATUS_TONES[status] ?? "neutral"} className={className}>
      {humanize(status)}
    </Badge>
  );
}
