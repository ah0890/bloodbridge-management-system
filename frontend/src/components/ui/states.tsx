import { AlertTriangle, Inbox, Loader2 } from "lucide-react";
import type { ReactNode } from "react";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "./button";

export function LoadingState({ label = "Loading…", className }: { label?: string; className?: string }) {
  return (
    <div role="status" className={cn("flex items-center justify-center gap-2 py-10 text-ink-subtle", className)}>
      <Loader2 className="size-4 animate-spin" aria-hidden />
      <span>{label}</span>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
  icon,
  className,
}: {
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  icon?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center justify-center px-6 py-10 text-center", className)}>
      <div className="mb-3 text-ink-subtle">{icon ?? <Inbox className="size-8" aria-hidden />}</div>
      <p className="font-medium text-ink">{title}</p>
      {description && <div className="mt-1 max-w-md text-sm text-ink-muted">{description}</div>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({ error, onRetry, className }: { error: unknown; onRetry?: () => void; className?: string }) {
  const message =
    error instanceof ApiError
      ? error.status === 403
        ? "You do not have permission to view this information."
        : error.message
      : "Something went wrong while loading this data.";
  return (
    <div role="alert" className={cn("flex flex-col items-center justify-center px-6 py-10 text-center", className)}>
      <AlertTriangle className="mb-3 size-8 text-danger" aria-hidden />
      <p className="font-medium text-ink">Unable to load</p>
      <p className="mt-1 max-w-md text-sm text-ink-muted">{message}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" className="mt-4" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}

export function Alert({
  tone = "info",
  title,
  children,
  className,
}: {
  tone?: "info" | "warning" | "danger" | "success" | "demo";
  title?: string;
  children?: ReactNode;
  className?: string;
}) {
  const tones = {
    info: "border-info/30 bg-info-soft text-info",
    warning: "border-warning/30 bg-warning-soft text-warning",
    danger: "border-danger/30 bg-danger-soft text-danger",
    success: "border-success/30 bg-success-soft text-success",
    demo: "border-demo/30 bg-demo-soft text-demo",
  };
  return (
    <div role={tone === "danger" ? "alert" : "note"} className={cn("rounded border px-3 py-2.5 text-sm", tones[tone], className)}>
      {title && <p className="font-semibold">{title}</p>}
      {children && <div className={cn("text-ink-muted", title && "mt-0.5")}>{children}</div>}
    </div>
  );
}
