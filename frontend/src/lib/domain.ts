import type { BloodGroup, Provenance } from "./types";

export type AvailabilityStatus = "available" | "unavailable" | "temporarily_deferred" | "unknown";
export type ConsentStatus = "granted" | "withdrawn";
export type DonorVerification = "unverified" | "phone_confirmed" | "screened";
export type ContactMethod = "phone" | "sms" | "whatsapp" | "email";
export type ContactOutcome =
  | "no_answer"
  | "declined"
  | "agreed_to_donate"
  | "reported_not_eligible"
  | "wrong_number"
  | "callback_requested";
export type Component = "whole_blood" | "red_cells" | "plasma" | "platelets" | "cryoprecipitate";
export type RequestStatus =
  | "submitted"
  | "under_review"
  | "searching"
  | "matches_found"
  | "coordination_in_progress"
  | "partially_fulfilled"
  | "fulfilled"
  | "cancelled"
  | "closed_unfulfilled";
export type Priority = "routine" | "urgent" | "critical";

export const AVAILABILITY: AvailabilityStatus[] = ["available", "unavailable", "temporarily_deferred", "unknown"];
export const VERIFICATION: DonorVerification[] = ["unverified", "phone_confirmed", "screened"];
export const CONTACT_METHODS: ContactMethod[] = ["phone", "sms", "whatsapp", "email"];
export const CONTACT_OUTCOMES: ContactOutcome[] = [
  "no_answer",
  "declined",
  "agreed_to_donate",
  "reported_not_eligible",
  "wrong_number",
  "callback_requested",
];
export const REQUEST_STATUSES: RequestStatus[] = [
  "submitted",
  "under_review",
  "searching",
  "matches_found",
  "coordination_in_progress",
  "partially_fulfilled",
  "fulfilled",
  "cancelled",
  "closed_unfulfilled",
];

export interface DonorListItem {
  id: number;
  code: string;
  display_name: string;
  blood_group: BloodGroup;
  city: string;
  locality: string | null;
  availability_status: AvailabilityStatus;
  availability_confirmed_at: string | null;
  consent_status: ConsentStatus;
  verification_status: DonorVerification;
  last_donation_date: string | null;
  registered_at: string;
  provenance: Provenance;
  is_active: boolean;
  currently_available: boolean;
}

export interface ContactAttempt {
  id: number;
  donor_id: number;
  request_id: number | null;
  attempted_at: string;
  method: ContactMethod;
  outcome: ContactOutcome;
  notes: string | null;
  provenance: Provenance;
}

export interface DonorDetail extends DonorListItem {
  date_of_birth: string | null;
  age: number | null;
  latitude: number | null;
  longitude: number | null;
  preferred_contact: ContactMethod;
  consent_at: string | null;
  anonymized_at: string | null;
  phone: string | null;
  email: string | null;
  staff_notes: string | null;
  consents: { status: ConsentStatus; scope: string; method: string; recorded_at: string }[];
  availability_history: {
    from_status: AvailabilityStatus | null;
    to_status: AvailabilityStatus;
    changed_at: string;
    source: string;
    note: string | null;
  }[];
  donations: {
    id: number;
    code: string;
    blood_bank_id: number;
    request_id: number | null;
    donated_on: string;
    component: Component;
    units: number;
    status: "completed" | "deferred_at_screening";
    provenance: Provenance;
    notes: string | null;
  }[];
  contact_attempts: ContactAttempt[];
}

export interface BloodBank {
  id: number;
  code: string;
  name: string;
  org_type: "blood_bank" | "hospital" | "hospital_blood_bank";
  city: string;
  address: string | null;
  phone: string | null;
  email: string | null;
  operating_hours: string | null;
  supported_components: Component[];
  verification_status: "pending" | "verified" | "rejected" | "suspended";
  provenance: Provenance;
  source_reference: string | null;
  last_verified_at: string | null;
  inventory_updated_at: string | null;
  is_active: boolean;
}
