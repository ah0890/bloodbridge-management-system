import type { Component, Priority, RequestStatus } from "@/lib/domain";
import type { BloodGroup, Provenance } from "@/lib/types";

export interface Kpis {
  registered_donors: number;
  available_donors: number;
  available_units: number;
  active_requests: number;
  critical_or_overdue_requests: number;
  verified_blood_banks: number;
  expiring_units: number;
  fulfilled_in_period: number;
  period_start: string;
  period_end: string;
}

export interface Summary {
  kpis: Kpis;
  stock_by_group: Record<BloodGroup, number>;
  thresholds: { low_stock_units: number; expiry_warning_days: number; availability_fresh_days: number; whole_blood_deferral_days: number };
  scope: { blood_bank_id: number | null; org_scoped: boolean };
}

export interface InventoryHealth {
  low_stock: { blood_group: BloodGroup; units: number; threshold: number }[];
  expiring: {
    id: number;
    code: string;
    blood_group: BloodGroup;
    component: Component;
    quantity: number;
    expires_on: string;
    blood_bank: string;
    city: string;
    provenance: Provenance;
  }[];
  excluded_units: Record<string, number>;
  wasted_last_30_days: number;
  recent_movements: {
    id: number;
    type: string;
    quantity: number;
    occurred_at: string;
    batch_code: string;
    blood_group: BloodGroup;
    component: Component;
    blood_bank: string;
    provenance: Provenance;
  }[];
}

export interface RequestBrief {
  id: number;
  code: string;
  blood_group: BloodGroup;
  component: Component;
  units_required: number;
  units_fulfilled: number;
  city: string;
  priority: Priority;
  status: RequestStatus;
  required_by: string;
  submitted_at: string;
  provenance: Provenance;
}

export interface RequestActivity {
  series: { date: string; received: number; fulfilled: number }[];
  by_status: Record<RequestStatus, number>;
  open_total: number;
  closed_total: number;
  open_by_priority: Record<Priority, number>;
  awaiting_coordination: RequestBrief[];
  recent_emergencies: RequestBrief[];
}

export interface ActivityEvent {
  at: string;
  kind: string;
  text: string;
  link: string;
  provenance: Provenance;
}

export interface CityRow {
  city: string;
  verified_banks: number;
  available_units: number;
  stock_by_group: Record<BloodGroup, number>;
  open_requests: number;
  available_donors: number;
  coverage_gap: boolean;
}
