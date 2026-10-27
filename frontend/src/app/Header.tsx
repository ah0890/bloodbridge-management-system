import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { Bell, ChevronDown, LogOut, Menu, Search } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { ROLE_LABELS } from "@/lib/types";
import { titleForPath } from "./nav";
import { useUnreadCount } from "./useUnreadCount";

export function Header({ onOpenMobile }: { onOpenMobile: () => void }) {
  const { session, logout, can } = useAuth();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const unread = useUnreadCount();
  const title = titleForPath(pathname);

  const onSearch = (e: FormEvent) => {
    e.preventDefault();
    const term = q.trim();
    if (term) navigate(`/search?q=${encodeURIComponent(term)}`);
  };

  if (!session) return null;
  const { user } = session;
  const initials = user.full_name
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <header className="sticky top-0 z-20 flex h-[var(--header-height)] items-center gap-3 border-b border-border bg-surface px-4">
      <button type="button" className="rounded p-1.5 text-ink-muted hover:bg-canvas lg:hidden" onClick={onOpenMobile} aria-label="Open navigation">
        <Menu className="size-5" />
      </button>

      <nav aria-label="Breadcrumb" className="min-w-0">
        <ol className="flex items-center gap-1.5 text-sm">
          <li className="hidden text-ink-subtle sm:block">
            <Link to="/" className="hover:text-ink">
              BloodBridge
            </Link>
          </li>
          <li className="hidden text-ink-subtle sm:block" aria-hidden>
            /
          </li>
          <li className="truncate font-semibold text-ink" aria-current="page">
            {title}
          </li>
        </ol>
      </nav>

      <form onSubmit={onSearch} className="ml-auto hidden w-full max-w-xs md:block" role="search">
        <label htmlFor="global-search" className="sr-only">
          Search requests, donors and blood banks
        </label>
        <div className="relative">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-ink-subtle" aria-hidden />
          <input
            id="global-search"
            className="input h-8 pl-8"
            placeholder="Search IDs, names, cities…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
      </form>

      <div className="ml-auto flex items-center gap-1 md:ml-0">
        <button
          type="button"
          className="rounded p-1.5 text-ink-muted hover:bg-canvas md:hidden"
          onClick={() => navigate("/search")}
          aria-label="Search"
        >
          <Search className="size-5" />
        </button>
        {can("notifications:view") && (
          <Link
            to="/notifications"
            className="relative rounded p-1.5 text-ink-muted hover:bg-canvas"
            aria-label={unread ? `Notifications, ${unread} unread` : "Notifications"}
          >
            <Bell className="size-5" />
            {unread > 0 && (
              <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-blood px-1 text-[10px] font-bold text-white">
                {unread > 99 ? "99+" : unread}
              </span>
            )}
          </Link>
        )}

        <DropdownMenu.Root>
          <DropdownMenu.Trigger className="flex items-center gap-2 rounded py-1 pl-1 pr-1.5 hover:bg-canvas" aria-label="User menu">
            <span className="flex size-7 items-center justify-center rounded-full bg-primary text-xs font-semibold text-white">{initials}</span>
            <span className="hidden text-left leading-tight lg:block">
              <span className="block text-xs font-semibold text-ink">{user.full_name}</span>
              <span className="block text-2xs text-ink-subtle">{ROLE_LABELS[user.role]}</span>
            </span>
            <ChevronDown className="size-4 text-ink-subtle" aria-hidden />
          </DropdownMenu.Trigger>
          <DropdownMenu.Portal>
            <DropdownMenu.Content align="end" sideOffset={6} className="z-50 w-64 rounded-md border border-border bg-surface p-1 shadow-pop">
              <div className="px-2.5 py-2">
                <p className="truncate text-sm font-semibold text-ink">{user.full_name}</p>
                <p className="truncate text-xs text-ink-subtle">{user.email}</p>
                <p className="mt-1 text-xs text-ink-muted">{ROLE_LABELS[user.role]}</p>
                {user.blood_bank && <p className="truncate text-xs text-ink-muted">{user.blood_bank.name}</p>}
              </div>
              <DropdownMenu.Separator className="my-1 h-px bg-border" />
              <DropdownMenu.Item
                className="flex cursor-pointer items-center gap-2 rounded px-2.5 py-2 text-sm text-ink outline-none data-[highlighted]:bg-canvas"
                onSelect={async () => {
                  await logout();
                  navigate("/login", { replace: true });
                }}
              >
                <LogOut className="size-4" aria-hidden /> Sign out
              </DropdownMenu.Item>
            </DropdownMenu.Content>
          </DropdownMenu.Portal>
        </DropdownMenu.Root>
      </div>
    </header>
  );
}
