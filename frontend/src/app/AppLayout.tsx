import { useEffect, useState } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { LoadingState } from "@/components/ui/states";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { DemoBanner } from "./DemoBanner";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";

const COLLAPSE_KEY = "bb.sidebar.collapsed";

function readCollapsed(): boolean {
  try {
    return localStorage.getItem(COLLAPSE_KEY) === "1";
  } catch {
    return false;
  }
}

export function AppLayout() {
  const { session, loading } = useAuth();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(readCollapsed);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    try {
      localStorage.setItem(COLLAPSE_KEY, collapsed ? "1" : "0");
    } catch {
      /* storage unavailable: preference simply isn't remembered */
    }
  }, [collapsed]);

  if (loading) return <LoadingState label="Checking session…" className="min-h-screen" />;
  if (!session) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;

  return (
    <div className="min-h-screen">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-surface focus:px-3 focus:py-2">
        Skip to content
      </a>
      <Sidebar
        collapsed={collapsed}
        onToggleCollapsed={() => setCollapsed((c) => !c)}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
      />
      <div className={cn("flex min-h-screen min-w-0 flex-col transition-[padding] duration-200", collapsed ? "lg:pl-[var(--sidebar-collapsed)]" : "lg:pl-[var(--sidebar-width)]")}>
        <Header onOpenMobile={() => setMobileOpen(true)} />
        <DemoBanner />
        <main id="main" className="mx-auto w-full min-w-0 max-w-[1600px] flex-1 px-4 py-5 sm:px-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
