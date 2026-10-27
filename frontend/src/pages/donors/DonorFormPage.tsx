import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useParams } from "react-router-dom";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader, PageHeader } from "@/components/ui/card";
import { Field } from "@/components/ui/form";
import { Alert, ErrorState, LoadingState } from "@/components/ui/states";
import { api, ApiError } from "@/lib/api";
import { AVAILABILITY, CONTACT_METHODS, VERIFICATION, type DonorDetail } from "@/lib/domain";
import { BLOOD_GROUPS } from "@/lib/types";
import { humanize } from "@/lib/utils";

const PHONE_RE = /^\+?[0-9][0-9\- ]{6,18}[0-9]$/;

function ageOn(dob: string): number {
  const d = new Date(dob + "T00:00:00");
  const now = new Date();
  let age = now.getFullYear() - d.getFullYear();
  if (now.getMonth() < d.getMonth() || (now.getMonth() === d.getMonth() && now.getDate() < d.getDate())) age--;
  return age;
}

const base = z.object({
  display_name: z.string().trim().min(2, "Name must be at least 2 characters").max(120),
  blood_group: z.enum(BLOOD_GROUPS, { errorMap: () => ({ message: "Select a blood group" }) }),
  date_of_birth: z
    .string()
    .optional()
    .refine((v) => !v || (ageOn(v) >= 18 && ageOn(v) <= 65), "Registration is limited to ages 18–65"),
  city: z.string().trim().min(2, "City is required").max(80),
  locality: z.string().trim().max(120).optional(),
  phone: z
    .string()
    .trim()
    .optional()
    .refine((v) => !v || PHONE_RE.test(v), "Enter a valid phone number"),
  email: z.union([z.literal(""), z.string().trim().email("Enter a valid email address")]).optional(),
  preferred_contact: z.enum(["phone", "sms", "whatsapp", "email"]),
  verification_status: z.enum(["unverified", "phone_confirmed", "screened"]),
  staff_notes: z.string().max(2000).optional(),
});

const createSchema = base
  .extend({
    availability_status: z.enum(["available", "unavailable", "temporarily_deferred", "unknown"]),
    last_donation_date: z
      .string()
      .optional()
      .refine((v) => !v || new Date(v) <= new Date(), "Last donation date cannot be in the future"),
    consent_method: z.enum(["paper_form", "online_form", "verbal_phone", "in_person"]),
    consent_confirmed: z.literal(true, { errorMap: () => ({ message: "Donor consent is required before registration" }) }),
  })
  .superRefine(contactRule);

const editSchema = base.superRefine(contactRule);

function contactRule(v: { preferred_contact: string; email?: string; phone?: string }, ctx: z.RefinementCtx) {
  if (v.preferred_contact === "email" && !v.email) ctx.addIssue({ code: "custom", path: ["email"], message: "Email is required for email contact" });
  if (v.preferred_contact !== "email" && !v.phone) ctx.addIssue({ code: "custom", path: ["phone"], message: "Phone is required for phone, SMS or WhatsApp" });
}

type CreateValues = z.infer<typeof createSchema>;

const blankToNull = (o: Record<string, unknown>) => Object.fromEntries(Object.entries(o).map(([k, v]) => [k, v === "" ? null : v]));

export function DonorFormPage() {
  const { id } = useParams();
  const editing = Boolean(id);
  const existing = useQuery({ queryKey: ["donor", id], queryFn: () => api.get<DonorDetail>(`/donors/${id}`), enabled: editing });
  if (editing && existing.isLoading) return <LoadingState />;
  if (editing && existing.isError) return <ErrorState error={existing.error} onRetry={() => existing.refetch()} />;
  return <DonorForm donor={existing.data} />;
}

function DonorForm({ donor }: { donor?: DonorDetail }) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [serverError, setServerError] = useState<string | null>(null);
  const editing = Boolean(donor);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<CreateValues>({
    resolver: zodResolver((editing ? editSchema : createSchema) as typeof createSchema),
    defaultValues: {
      preferred_contact: "phone",
      verification_status: "unverified",
      availability_status: "unknown",
      consent_method: "paper_form",
    },
  });

  useEffect(() => {
    if (donor)
      reset({
        display_name: donor.display_name,
        blood_group: donor.blood_group,
        date_of_birth: donor.date_of_birth ?? "",
        city: donor.city,
        locality: donor.locality ?? "",
        phone: donor.phone ?? "",
        email: donor.email ?? "",
        preferred_contact: donor.preferred_contact,
        verification_status: donor.verification_status,
        staff_notes: donor.staff_notes ?? "",
      } as CreateValues);
  }, [donor, reset]);

  const save = useMutation({
    mutationFn: (values: CreateValues) => {
      const body = blankToNull(values as unknown as Record<string, unknown>);
      return editing ? api.patch<DonorDetail>(`/donors/${donor!.id}`, body) : api.post<DonorDetail>("/donors", body);
    },
    onSuccess: (d) => {
      qc.invalidateQueries({ queryKey: ["donors"] });
      qc.setQueryData(["donor", String(d.id)], d);
      navigate(`/donors/${d.id}`);
    },
    onError: (e) => setServerError(e instanceof ApiError ? e.message : "Could not save the donor."),
  });

  const onSubmit = handleSubmit((v) => {
    setServerError(null);
    return save.mutateAsync(v).catch(() => undefined);
  });

  const err = (k: keyof CreateValues) => errors[k]?.message as string | undefined;

  return (
    <>
      <PageHeader
        title={editing ? `Edit ${donor!.display_name}` : "Register donor"}
        description={editing ? `${donor!.code} · availability and consent are updated from the donor profile, with a recorded source.` : "Collect only what coordination needs. Registration does not establish medical eligibility."}
      />
      <form onSubmit={onSubmit} noValidate className="max-w-4xl space-y-5">
        {serverError && <Alert tone="danger" title="Not saved">{serverError}</Alert>}
        <Card>
          <CardHeader title="Identity and blood group" />
          <CardBody className="grid gap-4 sm:grid-cols-2">
            <Field label="Display name" htmlFor="display_name" error={err("display_name")}>
              <input id="display_name" className="input" aria-invalid={!!errors.display_name} {...register("display_name")} />
            </Field>
            <Field label="Blood group" htmlFor="blood_group" error={err("blood_group")} hint="As reported by the donor or a previous screening">
              <select id="blood_group" className="input" aria-invalid={!!errors.blood_group} {...register("blood_group")}>
                <option value="">Select…</option>
                {BLOOD_GROUPS.map((g) => (
                  <option key={g}>{g}</option>
                ))}
              </select>
            </Field>
            <Field label="Date of birth (optional)" htmlFor="date_of_birth" error={err("date_of_birth")}>
              <input id="date_of_birth" type="date" className="input" aria-invalid={!!errors.date_of_birth} {...register("date_of_birth")} />
            </Field>
            <Field label="Verification" htmlFor="verification_status" error={err("verification_status")}>
              <select id="verification_status" className="input" {...register("verification_status")}>
                {VERIFICATION.map((v) => (
                  <option key={v} value={v}>
                    {humanize(v)}
                  </option>
                ))}
              </select>
            </Field>
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Location and contact" description="Contact details are visible only to coordinators and administrators." />
          <CardBody className="grid gap-4 sm:grid-cols-2">
            <Field label="City" htmlFor="city" error={err("city")}>
              <input id="city" className="input" aria-invalid={!!errors.city} {...register("city")} />
            </Field>
            <Field label="Locality (optional)" htmlFor="locality" error={err("locality")} hint="Area or sector only — never a home address">
              <input id="locality" className="input" {...register("locality")} />
            </Field>
            <Field label="Phone" htmlFor="phone" error={err("phone")}>
              <input id="phone" type="tel" className="input" aria-invalid={!!errors.phone} {...register("phone")} />
            </Field>
            <Field label="Email (optional)" htmlFor="email" error={err("email")}>
              <input id="email" type="email" className="input" aria-invalid={!!errors.email} {...register("email")} />
            </Field>
            <Field label="Preferred contact method" htmlFor="preferred_contact" error={err("preferred_contact")}>
              <select id="preferred_contact" className="input" {...register("preferred_contact")}>
                {CONTACT_METHODS.map((m) => (
                  <option key={m} value={m}>
                    {humanize(m)}
                  </option>
                ))}
              </select>
            </Field>
          </CardBody>
        </Card>

        {!editing && (
          <Card>
            <CardHeader title="Availability and consent" />
            <CardBody className="grid gap-4 sm:grid-cols-2">
              <Field label="Current availability" htmlFor="availability_status" hint="Only mark available after confirming with the donor">
                <select id="availability_status" className="input" {...register("availability_status")}>
                  {AVAILABILITY.map((a) => (
                    <option key={a} value={a}>
                      {humanize(a)}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Last donation date (if known)" htmlFor="last_donation_date" error={err("last_donation_date")}>
                <input id="last_donation_date" type="date" className="input" {...register("last_donation_date")} />
              </Field>
              <Field label="How consent was obtained" htmlFor="consent_method">
                <select id="consent_method" className="input" {...register("consent_method")}>
                  {["paper_form", "online_form", "verbal_phone", "in_person"].map((m) => (
                    <option key={m} value={m}>
                      {humanize(m)}
                    </option>
                  ))}
                </select>
              </Field>
              <div className="sm:col-span-2">
                <label className="flex items-start gap-2 text-sm text-ink">
                  <input type="checkbox" className="mt-0.5 size-4 accent-[rgb(var(--primary))]" {...register("consent_confirmed")} />
                  <span>
                    The donor has consented to BloodBridge storing these details and to being contacted by authorised coordinators about blood
                    requests. They can withdraw consent at any time.
                  </span>
                </label>
                {errors.consent_confirmed && <p className="mt-1 text-xs text-danger">{errors.consent_confirmed.message}</p>}
              </div>
            </CardBody>
          </Card>
        )}

        <Card>
          <CardHeader title="Staff notes (optional)" description="Visible only to coordinators and administrators. Do not record medical details." />
          <CardBody>
            <label htmlFor="staff_notes" className="sr-only">
              Staff notes
            </label>
            <textarea id="staff_notes" rows={3} className="input" {...register("staff_notes")} />
          </CardBody>
        </Card>

        <div className="flex flex-wrap gap-2">
          <Button type="submit" loading={isSubmitting}>
            {editing ? "Save changes" : "Register donor"}
          </Button>
          <Button variant="secondary" asChild>
            <Link to={editing ? `/donors/${donor!.id}` : "/donors"}>Cancel</Link>
          </Button>
        </div>
      </form>
    </>
  );
}
