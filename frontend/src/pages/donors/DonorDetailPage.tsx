import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Ban, Pencil, PhoneCall, RotateCcw, ShieldOff, UserX } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { BloodGroupBadge, ProvenanceBadge, StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader, PageHeader } from "@/components/ui/card";
import { Select } from "@/components/ui/form";
import { Alert, EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { AVAILABILITY, CONTACT_METHODS, CONTACT_OUTCOMES, type DonorDetail } from "@/lib/domain";
import { fmtDate, fmtDateTime, humanize } from "@/lib/utils";

export function DonorDetailPage() {
  const { id } = useParams();
  const { can, session } = useAuth();
  const qc = useQueryClient();
  const [message, setMessage] = useState<{ tone: "success" | "danger"; text: string } | null>(null);
  const donor = useQuery({ queryKey: ["donor", id], queryFn: () => api.get<DonorDetail>(`/donors/${id}`) });

  const action = useMutation({
    mutationFn: ({ path, body }: { path: string; body?: unknown; ok: string }) => api.post<DonorDetail>(`/donors/${id}/${path}`, body),
    onSuccess: (d, vars) => {
      if (d && "code" in d) qc.setQueryData(["donor", id], d);
      else qc.invalidateQueries({ queryKey: ["donor", id] });
      qc.invalidateQueries({ queryKey: ["donors"] });
      setMessage({ tone: "success", text: vars.ok });
    },
    onError: (e) => setMessage({ tone: "danger", text: e instanceof ApiError ? e.message : "Action failed." }),
  });

  if (donor.isLoading) return <LoadingState />;
  if (donor.isError || !donor.data) return <ErrorState error={donor.error} onRetry={() => donor.refetch()} />;
  const d = donor.data;
  const writable = can("donors:write") && !d.anonymized_at;
  const run = (path: string, ok: string, body?: unknown) => action.mutate({ path, body, ok });

  return (
    <>
      <PageHeader
        title={d.display_name}
        description={
          <span className="flex flex-wrap items-center gap-2">
            <span className="font-mono">{d.code}</span>
            <BloodGroupBadge group={d.blood_group} />
            <ProvenanceBadge provenance={d.provenance} />
            {!d.is_active && <StatusBadge status="unavailable" />}
          </span>
        }
        actions={
          writable && (
            <Button variant="secondary" asChild>
              <Link to={`/donors/${d.id}/edit`}>
                <Pencil /> Edit
              </Link>
            </Button>
          )
        }
      />
      {d.provenance === "synthetic" && (
        <Alert tone="demo" className="mb-4" title="Synthetic demonstration record">
          This is not a real person. The contact details are deliberately unreachable and BloodBridge never sends messages.
        </Alert>
      )}
      {message && (
        <Alert tone={message.tone} className="mb-4">
          {message.text}
        </Alert>
      )}

      <div className="grid gap-5 xl:grid-cols-3">
        <div className="space-y-5 xl:col-span-2">
          <Card>
            <CardHeader title="Profile" />
            <CardBody>
              <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
                <Item label="City">{d.city}{d.locality ? ` · ${d.locality}` : ""}</Item>
                <Item label="Age">{d.age ?? "—"}</Item>
                <Item label="Registered">{fmtDate(d.registered_at)}</Item>
                <Item label="Availability">
                  <StatusBadge status={d.availability_status} />{" "}
                  <span className="text-xs text-ink-subtle">{d.currently_available ? "counts as current" : "not current"}</span>
                </Item>
                <Item label="Availability confirmed">{fmtDateTime(d.availability_confirmed_at)}</Item>
                <Item label="Last donation">{fmtDate(d.last_donation_date)}</Item>
                <Item label="Consent">
                  <StatusBadge status={d.consent_status} /> <span className="text-xs text-ink-subtle">{fmtDate(d.consent_at)}</span>
                </Item>
                <Item label="Verification">
                  <StatusBadge status={d.verification_status} />
                </Item>
                <Item label="Preferred contact">{humanize(d.preferred_contact)}</Item>
                {can("donors:contact") ? (
                  <>
                    <Item label="Phone">{d.phone ?? "—"}</Item>
                    <Item label="Email">{d.email ?? "—"}</Item>
                  </>
                ) : (
                  <Item label="Contact details">Hidden for your role</Item>
                )}
              </dl>
              {d.staff_notes && (
                <div className="mt-4 rounded border border-border bg-canvas p-3 text-sm">
                  <p className="mb-1 text-xs font-semibold text-ink-muted">Staff notes</p>
                  <p className="whitespace-pre-wrap">{d.staff_notes}</p>
                </div>
              )}
              <p className="mt-4 text-xs text-ink-subtle">
                Blood-group match and availability do not establish eligibility. Final eligibility is decided by qualified staff at screening.
              </p>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Contact attempts" description="Records of contact made outside BloodBridge — nothing is sent from here" />
            {d.contact_attempts.length ? (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[560px]">
                  <thead className="border-b border-border bg-canvas/60">
                    <tr>
                      <th className="th">When</th>
                      <th className="th">Method</th>
                      <th className="th">Outcome</th>
                      <th className="th">Request</th>
                      <th className="th">Notes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {d.contact_attempts.map((c) => (
                      <tr key={c.id} className="border-b border-border last:border-0">
                        <td className="td whitespace-nowrap">{fmtDateTime(c.attempted_at)}</td>
                        <td className="td">{humanize(c.method)}</td>
                        <td className="td">{humanize(c.outcome)}</td>
                        <td className="td">{c.request_id ? <Link className="text-primary hover:underline" to={`/requests/${c.request_id}`}>#{c.request_id}</Link> : "—"}</td>
                        <td className="td text-ink-muted">{c.notes ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState title="No contact attempts recorded" />
            )}
          </Card>

          <div className="grid gap-5 lg:grid-cols-2">
            <Card>
              <CardHeader title="Donation history" />
              {d.donations.length ? (
                <ul className="divide-y divide-border">
                  {[...d.donations].reverse().map((x) => (
                    <li key={x.id} className="flex items-center justify-between gap-2 px-4 py-2 text-sm">
                      <span>
                        {fmtDate(x.donated_on)} · {humanize(x.component)}
                        <span className="block font-mono text-2xs text-ink-subtle">{x.code}</span>
                      </span>
                      <StatusBadge status={x.status === "completed" ? "fulfilled" : "temporarily_deferred"} />
                    </li>
                  ))}
                </ul>
              ) : (
                <EmptyState title="No donations recorded" />
              )}
            </Card>
            <Card>
              <CardHeader title="Availability & consent history" />
              <ul className="max-h-80 divide-y divide-border overflow-y-auto">
                {[
                  ...d.availability_history.map((h) => ({ at: h.changed_at, text: `Availability → ${humanize(h.to_status)}`, sub: humanize(h.source) + (h.note ? ` · ${h.note}` : "") })),
                  ...d.consents.map((c) => ({ at: c.recorded_at, text: `Consent ${c.status}`, sub: humanize(c.method) })),
                ]
                  .sort((a, b) => b.at.localeCompare(a.at))
                  .map((h, i) => (
                    <li key={i} className="px-4 py-2 text-sm">
                      {h.text}
                      <span className="block text-2xs text-ink-subtle">
                        {fmtDateTime(h.at)} · {h.sub}
                      </span>
                    </li>
                  ))}
              </ul>
            </Card>
          </div>
        </div>

        <div className="space-y-5">
          {can("donors:contact") && d.is_active && d.consent_status === "granted" && (
            <ContactForm busy={action.isPending} onSubmit={(body) => run("contact-attempts", "Contact attempt recorded.", body)} />
          )}
          {writable && d.is_active && (
            <AvailabilityForm
              current={d.availability_status}
              consent={d.consent_status}
              busy={action.isPending}
              onSubmit={(body) => run("availability", "Availability updated.", body)}
            />
          )}
          {writable && (
            <Card>
              <CardHeader title="Consent and record" />
              <CardBody className="space-y-2">
                {d.consent_status === "granted" ? (
                  <Button variant="secondary" className="w-full" onClick={() => confirm("Record that this donor has withdrawn consent? They will be marked unavailable.") && run("consent", "Consent withdrawal recorded.", { status: "withdrawn", method: "verbal_phone" })}>
                    <ShieldOff /> Record consent withdrawal
                  </Button>
                ) : (
                  <Button variant="secondary" className="w-full" onClick={() => confirm("Record that this donor has given consent again?") && run("consent", "Consent recorded.", { status: "granted", method: "verbal_phone" })}>
                    <RotateCcw /> Record renewed consent
                  </Button>
                )}
                {d.is_active ? (
                  <Button variant="secondary" className="w-full" onClick={() => confirm("Deactivate this donor record? It is kept for audit purposes.") && run("deactivate", "Donor deactivated.")}>
                    <Ban /> Deactivate record
                  </Button>
                ) : (
                  <Button variant="secondary" className="w-full" onClick={() => run("reactivate", "Donor reactivated.")}>
                    <RotateCcw /> Reactivate record
                  </Button>
                )}
                {session?.user.role === "admin" && (
                  <Button
                    variant="danger"
                    className="w-full"
                    onClick={() => confirm("Permanently anonymise this donor? Name, contact details, date of birth and notes are erased. This cannot be undone.") && run("anonymize", "Donor anonymised.")}
                  >
                    <UserX /> Anonymise (irreversible)
                  </Button>
                )}
              </CardBody>
            </Card>
          )}
          {d.anonymized_at && <Alert tone="info" title={`Anonymised ${fmtDate(d.anonymized_at)}`}>Personal data has been erased; aggregate history is retained.</Alert>}
        </div>
      </div>
    </>
  );
}

function Item({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-ink-subtle">{label}</dt>
      <dd className="mt-0.5 break-words text-ink">{children}</dd>
    </div>
  );
}

function ContactForm({ busy, onSubmit }: { busy: boolean; onSubmit: (b: unknown) => void }) {
  const [method, setMethod] = useState("phone");
  const [outcome, setOutcome] = useState("no_answer");
  const [requestId, setRequestId] = useState("");
  const [notes, setNotes] = useState("");
  const submit = (e: FormEvent) => {
    e.preventDefault();
    onSubmit({ method, outcome, notes: notes || null, request_id: requestId ? Number(requestId) : null });
    setNotes("");
  };
  return (
    <Card>
      <CardHeader title="Record contact attempt" description="Log a call or message you made yourself" />
      <CardBody>
        <form onSubmit={submit} className="space-y-3">
          <Select id="c-method" label="Method" options={CONTACT_METHODS} value={method} onChange={(e) => setMethod(e.target.value)} />
          <Select id="c-outcome" label="Outcome" options={CONTACT_OUTCOMES} value={outcome} onChange={(e) => setOutcome(e.target.value)} />
          <div>
            <label htmlFor="c-req" className="field-label">
              Related request ID (optional)
            </label>
            <input id="c-req" inputMode="numeric" pattern="[0-9]*" className="input" value={requestId} onChange={(e) => setRequestId(e.target.value.replace(/\D/g, ""))} />
          </div>
          <div>
            <label htmlFor="c-notes" className="field-label">
              Notes
            </label>
            <textarea id="c-notes" rows={2} maxLength={500} className="input" value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>
          <Button type="submit" className="w-full" loading={busy}>
            <PhoneCall /> Save attempt
          </Button>
        </form>
      </CardBody>
    </Card>
  );
}

function AvailabilityForm({ current, consent, busy, onSubmit }: { current: string; consent: string; busy: boolean; onSubmit: (b: unknown) => void }) {
  const [status, setStatus] = useState(current);
  const [source, setSource] = useState("donor_phone_confirmation");
  const [note, setNote] = useState("");
  return (
    <Card>
      <CardHeader title="Update availability" description="Record only what the donor has confirmed" />
      <CardBody>
        <form
          className="space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit({ status, source, note: note || null });
          }}
        >
          <Select id="a-status" label="Availability" options={AVAILABILITY} value={status} onChange={(e) => setStatus(e.target.value)} />
          <Select id="a-source" label="Source" options={["donor_phone_confirmation", "donor_in_person", "contact_attempt", "staff_review"]} value={source} onChange={(e) => setSource(e.target.value)} />
          <div>
            <label htmlFor="a-note" className="field-label">
              Note (optional)
            </label>
            <input id="a-note" maxLength={300} className="input" value={note} onChange={(e) => setNote(e.target.value)} />
          </div>
          {status === "available" && consent !== "granted" && <p className="text-xs text-danger">A donor without consent cannot be marked available.</p>}
          <Button type="submit" className="w-full" loading={busy} disabled={status === "available" && consent !== "granted"}>
            Confirm availability
          </Button>
        </form>
      </CardBody>
    </Card>
  );
}
