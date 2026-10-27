import { ChevronsLeft, ChevronsRight, Droplet, X } from "lucide-react";
import { NavLink } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { NAV_ITEMS } from "./nav";

interface Props {
  collapsed: boolean;
  onToggleCollapsed: () => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
}

export function Sidebar({ collapsed, onToggleCollapsed, mobileOpen, onCloseMobile }: Props) {
  const { can } = useAuth();
  const items = NAV_ITEMS.filter((i) => can(i.perm));

  return (
    <>
      {mobileOpen && <div className="fixed inset-0 z-30 bg-ink/40 lg:hidden" onClick={onCloseMobile} aria-hidden />}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex flex-col bg-nav text-nav-fg transition-[width,transform] duration-200",
          "w-[var(--sidebar-width)] -translate-x-full lg:translate-x-0",
          mobileOpen && "translate-x-0",
          collapsed && "lg:w-[var(--sidebar-collapsed)]",
        )}
        aria-label="Primary navigation"
      >
        <div className="flex h-[var(--header-height)] items-center gap-2 border-b border-white/10 px-4">
          <span className="flex size-7 shrink-0 items-center justify-center rounded bg-blood">
            <Droplet className="size-4 fill-white text-white" aria-hidden />
          </span>
          <span className={cn("truncate text-[15px] font-semibold tracking-tight text-white", collapsed && "lg:hidden")}>
            BloodBridge
          </span>
          <button
            type="button"
            className="ml-auto rounded p-1 text-nav-muted hover:text-white lg:hidden"
            onClick={onCloseMobile}
            aria-label="Close navigation"
          >
            <X className="size-5" />
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto px-2 py-3">
          <ul className="space-y-0.5">
            {items.map(({ to, label, icon: Icon }) => (
              <li key={to}>
                <NavLink
                  to={to}
                  end={to === "/"}
                  onClick={onCloseMobile}
                  title={collapsed ? label : undefined}
                  className={({ isActive }) =>
                    cn(
                      "flex h-9 items-center gap-3 rounded px-2.5 text-[13px] font-medium transition-colors",
                      isActive ? "bg-nav-active text-white" : "text-nav-muted hover:bg-white/5 hover:text-white",
                      collapsed && "lg:justify-center lg:px-0",
                    )
                  }
                >
                  {({ isActive }) => (
                    <>
                      <Icon className={cn("size-[18px] shrink-0", isActive && "text-blood-soft")} aria-hidden />
                      <span className={cn("truncate", collapsed && "lg:sr-only")}>{label}</span>
                    </>
                  )}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <div className="hidden border-t border-white/10 p-2 lg:block">
          <button
            type="button"
            onClick={onToggleCollapsed}
            className={cn(
              "flex h-8 w-full items-center gap-2 rounded px-2.5 text-xs text-nav-muted hover:bg-white/5 hover:text-white",
              collapsed && "justify-center px-0",
            )}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <ChevronsRight className="size-4" /> : <ChevronsLeft className="size-4" />}
            {!collapsed && <span>Collapse</span>}
          </button>
        </div>
      </aside>
    </>
  );
}
