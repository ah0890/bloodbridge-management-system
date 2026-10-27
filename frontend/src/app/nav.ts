import {
  Activity,
  Bell,
  Building2,
  ClipboardList,
  Droplets,
  FileBarChart,
  HeartHandshake,
  LayoutDashboard,
  MapPinned,
  ScrollText,
  Settings,
  UserCog,
  Users,
  type LucideIcon,
} from "lucide-react";
import type { Permission } from "@/lib/types";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  perm: Permission;
}

/** Sidebar order follows the product specification. Items are filtered by server-issued permissions. */
export const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Overview", icon: LayoutDashboard, perm: "dashboard:view" },
  { to: "/donors", label: "Donors", icon: Users, perm: "donors:read" },
  { to: "/inventory", label: "Blood Inventory", icon: Droplets, perm: "inventory:read" },
  { to: "/requests", label: "Blood Requests", icon: ClipboardList, perm: "requests:read" },
  { to: "/matching", label: "Donor Matching", icon: HeartHandshake, perm: "matching:run" },
  { to: "/blood-banks", label: "Blood Banks", icon: Building2, perm: "banks:read" },
  { to: "/geography", label: "Geographic Availability", icon: MapPinned, perm: "geo:view" },
  { to: "/donations", label: "Donations", icon: Activity, perm: "donations:read" },
  { to: "/reports", label: "Reports & Analytics", icon: FileBarChart, perm: "reports:view" },
  { to: "/notifications", label: "Notifications", icon: Bell, perm: "notifications:view" },
  { to: "/audit", label: "Audit Logs", icon: ScrollText, perm: "audit:read" },
  { to: "/users", label: "User Management", icon: UserCog, perm: "users:manage" },
  { to: "/settings", label: "Settings", icon: Settings, perm: "settings:manage" },
];

export function titleForPath(pathname: string): string {
  if (pathname === "/") return "Overview";
  const match = [...NAV_ITEMS].filter((n) => n.to !== "/").find((n) => pathname.startsWith(n.to));
  return match?.label ?? "BloodBridge";
}
