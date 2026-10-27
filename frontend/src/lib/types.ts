export type Role = "admin" | "bank_manager" | "coordinator";

export type Permission =
  | "dashboard:view"
  | "donors:read"
  | "donors:write"
  | "donors:contact"
  | "donors:export"
  | "donations:read"
  | "donations:write"
  | "inventory:read"
  | "inventory:write"
  | "requests:read"
  | "requests:manage"
  | "matching:run"
  | "banks:read"
  | "banks:manage"
  | "banks:edit_own"
  | "geo:view"
  | "reports:view"
  | "reports:export"
  | "notifications:view"
  | "audit:read"
  | "users:manage"
  | "settings:manage"
  | "imports:run";

export interface BloodBankRef {
  id: number;
  name: string;
  city: string;
  provenance: Provenance;
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  blood_bank: BloodBankRef | null;
  is_active: boolean;
  is_demo: boolean;
  last_login_at: string | null;
}

export interface SessionInfo {
  user: User;
  permissions: Permission[];
  csrf_token: string;
  expires_at: string | null;
}

export type Provenance = "synthetic" | "imported" | "verified";

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export const BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"] as const;
export type BloodGroup = (typeof BLOOD_GROUPS)[number];

export const ROLE_LABELS: Record<Role, string> = {
  admin: "Platform Administrator",
  bank_manager: "Blood Bank Manager",
  coordinator: "Donor Coordinator",
};
