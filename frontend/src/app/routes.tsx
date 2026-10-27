import { createBrowserRouter, type RouteObject } from "react-router-dom";
import { LoginPage } from "@/pages/LoginPage";
import { NotFoundPage, UnavailablePage } from "@/pages/UnavailablePage";
import type { Permission } from "@/lib/types";
import { AppLayout } from "./AppLayout";
import { RequirePerm } from "./RequirePerm";

function guarded(path: string, perm: Permission, element: JSX.Element): RouteObject {
  return { path, element: <RequirePerm perm={perm}>{element}</RequirePerm> };
}

const later = (title: string, milestone: string) => <UnavailablePage title={title} milestone={milestone} />;

export const routes: RouteObject[] = [
  { path: "/login", element: <LoginPage /> },
  { path: "/public/*", element: later("Public portal", "Milestone 4") },
  {
    path: "/",
    element: <AppLayout />,
    children: [
      guarded("/", "dashboard:view", later("Overview", "Milestone 3")),
      guarded("/donors/*", "donors:read", later("Donors", "Milestone 3")),
      guarded("/inventory/*", "inventory:read", later("Blood Inventory", "Milestone 4")),
      guarded("/requests/*", "requests:read", later("Blood Requests", "Milestone 4")),
      guarded("/matching/*", "matching:run", later("Donor Matching", "Milestone 5")),
      guarded("/blood-banks/*", "banks:read", later("Blood Banks", "Milestone 3")),
      guarded("/geography", "geo:view", later("Geographic Availability", "Milestone 5")),
      guarded("/donations", "donations:read", later("Donations", "Milestone 4")),
      guarded("/reports", "reports:view", later("Reports & Analytics", "Milestone 6")),
      guarded("/notifications", "notifications:view", later("Notifications", "Milestone 6")),
      guarded("/audit", "audit:read", later("Audit Logs", "Milestone 6")),
      guarded("/users", "users:manage", later("User Management", "Milestone 6")),
      guarded("/settings", "settings:manage", later("Settings", "Milestone 6")),
      { path: "/search", element: later("Search", "Milestone 3") },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];

export const router = createBrowserRouter(routes);
