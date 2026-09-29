import { useEffect, useMemo, useState } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import {
  ShieldCheck,
  Warning,
  Buildings,
  Scales,
  ListChecks,
  Plus,
  Trash,
  CheckSquare,
  Square,
  CalendarBlank,
  CircleNotch,
} from "@phosphor-icons/react";

// ---- helpers --------------------------------------------------------------
const STATUS_STYLES = {
  green: {
    dot: "bg-emerald-500",
    pill: "bg-emerald-100 text-emerald-900 border-emerald-700",
    row: "bg-emerald-50/60",
    label: "DPF certified",
  },
  amber: {
    dot: "bg-amber-500",
    pill: "bg-amber-100 text-amber-900 border-amber-700",
    row: "bg-amber-50/60",
    label: "IDTA in place",
  },
  red: {
    dot: "bg-rose-500",
    pill: "bg-rose-100 text-rose-900 border-rose-700",
    row: "bg-rose-50/70",
    label: "No mechanism",
  },
};

function fmtDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" });
}

function StatusPill({ status, label }) {
  const s = STATUS_STYLES[status] || STATUS_STYLES.red;
  return (
    <span
      data-testid={`status-pill-${status}`}
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border-2 text-xs font-bold ${s.pill}`}
    >
      <span className={`w-2 h-2 rounded-full ${s.dot}`} />
      {label || s.label}
    </span>
  );
}

// ---- Alerts banner --------------------------------------------------------
function AlertsBanner({ alerts, loading }) {
  if (loading) {
    return (
      <div className="brutal-card p-4 bg-white flex items-center gap-2 text-sm">
        <CircleNotch size={16} className="animate-spin" /> Loading alerts…
      </div>
    );
  }
  if (!alerts) return null;
  const anyIssue =
    alerts.dpf_expiring_within_60_days.length ||
    alerts.tra_stale_or_missing.length ||
    alerts.no_transfer_mechanism.length;

  if (!anyIssue) {
    return (
      <div className="brutal-card p-4 bg-emerald-50 flex items-center gap-3" data-testid="alerts-all-clear">
        <ShieldCheck size={22} weight="fill" className="text-emerald-700" />
        <div>
          <div className="font-display font-extrabold text-lg">All clear</div>
          <div className="text-sm text-slate-700">
            No DPF certs expiring in the next 60 days · no stale TRAs · every recipient has a mechanism.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="brutal-card p-4 bg-amber-50" data-testid="alerts-issues">
      <div className="flex items-center gap-2 mb-3">
        <Warning size={20} weight="fill" className="text-amber-700" />
        <h3 className="font-display font-extrabold text-lg">Attention required</h3>
      </div>
      <div className="grid md:grid-cols-3 gap-3">
        <div className="rounded-md border-2 border-rose-700 bg-white p-3" data-testid="alert-dpf-expiring">
          <div className="text-xs uppercase tracking-widest font-bold text-rose-800">DPF expiring &lt;60d</div>
          <div className="font-display font-black text-3xl">{alerts.dpf_expiring_within_60_days.length}</div>
          {alerts.dpf_expiring_within_60_days.slice(0, 3).map((a) => (
            <div key={a.id} className="text-xs mt-1">
              <span className="font-bold">{a.company_name}</span> · {a.days_to_expiry}d left ({fmtDate(a.dpf_expiry_date)})
            </div>
          ))}
        </div>
        <div className="rounded-md border-2 border-amber-700 bg-white p-3" data-testid="alert-tra-stale">
          <div className="text-xs uppercase tracking-widest font-bold text-amber-800">TRA stale / missing</div>
          <div className="font-display font-black text-3xl">{alerts.tra_stale_or_missing.length}</div>
          {alerts.tra_stale_or_missing.slice(0, 3).map((a) => (
            <div key={a.id} className="text-xs mt-1">
              <span className="font-bold">{a.company_name}</span> ·{" "}
              {a.missing ? "no TRA on file" : `${a.days_old}d old`}
            </div>
          ))}
        </div>
        <div className="rounded-md border-2 border-rose-700 bg-white p-3" data-testid="alert-no-mechanism">
          <div className="text-xs uppercase tracking-widest font-bold text-rose-800">No transfer mechanism</div>
          <div className="font-display font-black text-3xl">{alerts.no_transfer_mechanism.length}</div>
          {alerts.no_transfer_mechanism.slice(0, 3).map((a) => (
            <div key={a.id} className="text-xs mt-1 font-bold">{a.company_name}</div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ---- Recipients section ---------------------------------------------------
const EMPTY_RECIPIENT = {
  company_name: "",
  dpf_certified: false,
  dpf_expiry_date: "",
  idta_in_place: false,
  tra_date: "",
  notes: "",
};

function RecipientsSection({ recipients, refresh }) {
  const [form, setForm] = useState(EMPTY_RECIPIENT);
  const [saving, setSaving] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.company_name.trim()) {
      toast.error("Company name is required");
      return;
    }
    setSaving(true);
    try {
      await api.post("/compliance/recipients", {
        ...form,
        dpf_expiry_date: form.dpf_expiry_date || null,
        tra_date: form.tra_date || null,
      });
      toast.success("Recipient added");
      setForm(EMPTY_RECIPIENT);
      await refresh();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not save");
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id) => {
    if (!window.confirm("Remove this recipient?")) return;
    try {
      await api.delete(`/compliance/recipients/${id}`);
      toast.success("Removed");
      await refresh();
    } catch {
      toast.error("Could not delete");
    }
  };

  return (
    <section className="brutal-card p-5 bg-white" data-testid="section-recipients">
      <header className="flex items-center gap-2 mb-1">
        <Buildings size={22} weight="bold" />
        <h2 className="font-display font-extrabold text-2xl">Transfer Mechanism Tracker</h2>
      </header>
      <p className="text-sm text-slate-600 mb-4">
        Every US-based data recipient, the mechanism keeping the transfer lawful, and the last Transfer Risk
        Assessment. Rows are colour-coded by status.
      </p>

      <form
        onSubmit={submit}
        className="grid md:grid-cols-6 gap-2 mb-5 p-3 rounded-md border-2 border-ink bg-butter/60"
        data-testid="recipient-form"
      >
        <input
          data-testid="recipient-company-input"
          className="md:col-span-2 rounded-md border-2 border-ink px-2 py-1.5 bg-white text-sm"
          placeholder="Company name"
          value={form.company_name}
          onChange={(e) => setForm({ ...form, company_name: e.target.value })}
        />
        <label className="flex items-center gap-2 text-sm font-semibold px-2 py-1.5 rounded-md border-2 border-ink bg-white">
          <input
            type="checkbox"
            data-testid="recipient-dpf-checkbox"
            checked={form.dpf_certified}
            onChange={(e) => setForm({ ...form, dpf_certified: e.target.checked })}
          />
          DPF certified
        </label>
        <input
          type="date"
          data-testid="recipient-dpf-expiry"
          className="rounded-md border-2 border-ink px-2 py-1.5 bg-white text-sm"
          placeholder="DPF expiry"
          value={form.dpf_expiry_date}
          onChange={(e) => setForm({ ...form, dpf_expiry_date: e.target.value })}
        />
        <label className="flex items-center gap-2 text-sm font-semibold px-2 py-1.5 rounded-md border-2 border-ink bg-white">
          <input
            type="checkbox"
            data-testid="recipient-idta-checkbox"
            checked={form.idta_in_place}
            onChange={(e) => setForm({ ...form, idta_in_place: e.target.checked })}
          />
          IDTA / UK SCC
        </label>
        <input
          type="date"
          data-testid="recipient-tra-date"
          className="rounded-md border-2 border-ink px-2 py-1.5 bg-white text-sm"
          placeholder="Last TRA date"
          value={form.tra_date}
          onChange={(e) => setForm({ ...form, tra_date: e.target.value })}
        />
        <input
          data-testid="recipient-notes-input"
          className="md:col-span-5 rounded-md border-2 border-ink px-2 py-1.5 bg-white text-sm"
          placeholder="Notes (data categories, hosting region, sub-processors…)"
          value={form.notes}
          onChange={(e) => setForm({ ...form, notes: e.target.value })}
        />
        <button
          type="submit"
          data-testid="recipient-add-btn"
          disabled={saving}
          className="brutal-btn bg-mint inline-flex items-center justify-center gap-1.5 text-sm py-1.5"
        >
          <Plus size={14} weight="bold" /> {saving ? "Saving…" : "Add"}
        </button>
      </form>

      {recipients.length === 0 ? (
        <div className="text-sm text-slate-600 italic" data-testid="recipients-empty">
          No US recipients logged yet.
        </div>
      ) : (
        <div className="overflow-x-auto brutal-card bg-white">
          <table className="min-w-full text-sm" data-testid="recipients-table">
            <thead className="bg-slate-50 border-b-2 border-ink">
              <tr className="text-left">
                <th className="p-3 font-display">Status</th>
                <th className="p-3 font-display">Company</th>
                <th className="p-3 font-display">DPF cert</th>
                <th className="p-3 font-display">DPF expiry</th>
                <th className="p-3 font-display">IDTA / SCC</th>
                <th className="p-3 font-display">Last TRA</th>
                <th className="p-3 font-display">Notes</th>
                <th className="p-3 font-display text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {recipients.map((r) => {
                const style = STATUS_STYLES[r.status] || STATUS_STYLES.red;
                return (
                  <tr
                    key={r.id}
                    className={`border-t border-ink/20 ${style.row}`}
                    data-testid={`recipient-row-${r.id}`}
                  >
                    <td className="p-3">
                      <StatusPill status={r.status} label={r.status_label} />
                    </td>
                    <td className="p-3 font-bold">{r.company_name}</td>
                    <td className="p-3">{r.dpf_certified ? "✓" : "—"}</td>
                    <td className="p-3">
                      {fmtDate(r.dpf_expiry_date)}
                      {r.dpf_expiring_soon && (
                        <span className="ml-1 text-[10px] px-1.5 py-0.5 border-2 border-rose-700 rounded bg-rose-100 text-rose-900 font-bold">
                          {r.dpf_days_to_expiry}d
                        </span>
                      )}
                    </td>
                    <td className="p-3">{r.idta_in_place ? "✓" : "—"}</td>
                    <td className="p-3">
                      {fmtDate(r.tra_date)}
                      {(r.tra_stale || r.tra_missing) && (
                        <span className="ml-1 text-[10px] px-1.5 py-0.5 border-2 border-amber-700 rounded bg-amber-100 text-amber-900 font-bold">
                          {r.tra_missing ? "missing" : "stale"}
                        </span>
                      )}
                    </td>
                    <td className="p-3 max-w-[220px] truncate" title={r.notes}>{r.notes || "—"}</td>
                    <td className="p-3 text-right">
                      <button
                        onClick={() => remove(r.id)}
                        data-testid={`recipient-delete-${r.id}`}
                        className="inline-flex items-center gap-1 px-2 py-1 rounded border-2 border-ink bg-white hover:bg-rose-100 text-xs font-bold"
                      >
                        <Trash size={12} weight="bold" /> Delete
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

// ---- CLOUD Act log --------------------------------------------------------
const EMPTY_INCIDENT = {
  date: new Date().toISOString().slice(0, 10),
  authority: "",
  request_type: "",
  data_categories: "",
  handling: "",
};

function CloudActSection({ incidents, refresh }) {
  const [form, setForm] = useState(EMPTY_INCIDENT);
  const [saving, setSaving] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.request_type.trim() || !form.handling.trim()) {
      toast.error("Type of request and handling are required");
      return;
    }
    setSaving(true);
    try {
      await api.post("/compliance/cloud-act", form);
      toast.success("Incident logged");
      setForm({ ...EMPTY_INCIDENT, date: new Date().toISOString().slice(0, 10) });
      await refresh();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not save");
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id) => {
    if (!window.confirm("Remove this incident?")) return;
    try {
      await api.delete(`/compliance/cloud-act/${id}`);
      toast.success("Removed");
      await refresh();
    } catch {
      toast.error("Could not delete");
    }
  };

  return (
    <section className="brutal-card p-5 bg-white" data-testid="section-cloud-act">
      <header className="flex items-center gap-2 mb-1">
        <Scales size={22} weight="bold" />
        <h2 className="font-display font-extrabold text-2xl">CLOUD Act Risk Log</h2>
      </header>
      <p className="text-sm text-slate-600 mb-4">
        Any incident where a US authority requested access to personal data — with date, request type, and how it
        was handled.
      </p>

      <form
        onSubmit={submit}
        className="grid md:grid-cols-6 gap-2 mb-5 p-3 rounded-md border-2 border-ink bg-lavender/50"
        data-testid="incident-form"
      >
        <input
          type="date"
          data-testid="incident-date-input"
          className="rounded-md border-2 border-ink px-2 py-1.5 bg-white text-sm"
          value={form.date}
          onChange={(e) => setForm({ ...form, date: e.target.value })}
        />
        <input
          data-testid="incident-authority-input"
          className="rounded-md border-2 border-ink px-2 py-1.5 bg-white text-sm"
          placeholder="Authority (e.g. FBI)"
          value={form.authority}
          onChange={(e) => setForm({ ...form, authority: e.target.value })}
        />
        <input
          data-testid="incident-type-input"
          className="md:col-span-2 rounded-md border-2 border-ink px-2 py-1.5 bg-white text-sm"
          placeholder="Type of request (subpoena, MLAT, National Security Letter…)"
          value={form.request_type}
          onChange={(e) => setForm({ ...form, request_type: e.target.value })}
        />
        <input
          data-testid="incident-categories-input"
          className="md:col-span-2 rounded-md border-2 border-ink px-2 py-1.5 bg-white text-sm"
          placeholder="Data categories affected"
          value={form.data_categories}
          onChange={(e) => setForm({ ...form, data_categories: e.target.value })}
        />
        <textarea
          data-testid="incident-handling-input"
          rows={2}
          className="md:col-span-5 rounded-md border-2 border-ink px-2 py-1.5 bg-white text-sm"
          placeholder="How the request was handled (challenged, disclosed, notified data subject, DPO consulted…)"
          value={form.handling}
          onChange={(e) => setForm({ ...form, handling: e.target.value })}
        />
        <button
          type="submit"
          data-testid="incident-add-btn"
          disabled={saving}
          className="brutal-btn bg-peach inline-flex items-center justify-center gap-1.5 text-sm py-1.5"
        >
          <Plus size={14} weight="bold" /> {saving ? "Saving…" : "Log incident"}
        </button>
      </form>

      {incidents.length === 0 ? (
        <div className="text-sm text-slate-600 italic" data-testid="incidents-empty">
          No CLOUD Act incidents logged. Keeping this empty is good — but log every request even if challenged.
        </div>
      ) : (
        <ol className="space-y-3" data-testid="incidents-list">
          {incidents.map((i) => (
            <li
              key={i.id}
              className="rounded-md border-2 border-ink bg-slate-50 p-3"
              data-testid={`incident-row-${i.id}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-full border-2 border-ink bg-white">
                      <CalendarBlank size={12} /> {fmtDate(i.date)}
                    </span>
                    <span className="text-sm font-bold">{i.request_type}</span>
                    {i.authority && (
                      <span className="text-xs px-2 py-0.5 rounded-full border-2 border-ink bg-butter">
                        {i.authority}
                      </span>
                    )}
                  </div>
                  {i.data_categories && (
                    <div className="text-xs text-slate-700 mt-1">
                      <span className="font-bold">Data categories: </span>
                      {i.data_categories}
                    </div>
                  )}
                  <div className="text-sm mt-2 whitespace-pre-wrap">{i.handling}</div>
                </div>
                <button
                  onClick={() => remove(i.id)}
                  data-testid={`incident-delete-${i.id}`}
                  className="inline-flex items-center gap-1 px-2 py-1 rounded border-2 border-ink bg-white hover:bg-rose-100 text-xs font-bold"
                >
                  <Trash size={12} weight="bold" /> Delete
                </button>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

// ---- Checklist ------------------------------------------------------------
function ChecklistSection({ items, refresh }) {
  const [busy, setBusy] = useState(null);

  const toggle = async (item) => {
    setBusy(item.key);
    try {
      await api.patch("/compliance/checklist", { key: item.key, checked: !item.checked });
      await refresh();
    } catch {
      toast.error("Could not update");
    } finally {
      setBusy(null);
    }
  };

  const doneCount = items.filter((i) => i.checked).length;
  const progress = items.length ? Math.round((doneCount / items.length) * 100) : 0;

  return (
    <section className="brutal-card p-5 bg-white" data-testid="section-checklist">
      <header className="flex items-center gap-2 mb-1">
        <ListChecks size={22} weight="bold" />
        <h2 className="font-display font-extrabold text-2xl">Compliance Checklist</h2>
      </header>
      <div className="flex items-center gap-3 mb-4">
        <div className="flex-1 h-2 rounded-full bg-slate-200 overflow-hidden border-2 border-ink">
          <div
            className={`h-full ${progress === 100 ? "bg-emerald-500" : "bg-butter"}`}
            style={{ width: `${progress}%` }}
            data-testid="checklist-progress-bar"
          />
        </div>
        <div className="text-sm font-mono font-bold" data-testid="checklist-progress">
          {doneCount}/{items.length}
        </div>
      </div>

      <ul className="space-y-2">
        {items.map((it) => (
          <li
            key={it.key}
            className={`flex items-start gap-3 p-3 rounded-md border-2 border-ink ${
              it.checked ? "bg-emerald-50" : "bg-white"
            }`}
            data-testid={`checklist-item-${it.key}`}
          >
            <button
              onClick={() => toggle(it)}
              disabled={busy === it.key}
              className="mt-0.5 shrink-0"
              data-testid={`checklist-toggle-${it.key}`}
              aria-label={it.checked ? "Uncheck" : "Check"}
            >
              {it.checked ? (
                <CheckSquare size={22} weight="fill" className="text-emerald-700" />
              ) : (
                <Square size={22} weight="bold" />
              )}
            </button>
            <div className="flex-1">
              <div className={`font-semibold ${it.checked ? "line-through text-slate-500" : ""}`}>
                {it.label}
              </div>
              {it.checked_at && (
                <div className="text-xs text-slate-600">Confirmed {fmtDate(it.checked_at)}</div>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

// ---- Page ----------------------------------------------------------------
export default function Compliance() {
  const { user } = useAuth();
  const [recipients, setRecipients] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [checklist, setChecklist] = useState([]);
  const [alerts, setAlerts] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadAll = async () => {
    try {
      const [r, i, c, a] = await Promise.all([
        api.get("/compliance/recipients"),
        api.get("/compliance/cloud-act"),
        api.get("/compliance/checklist"),
        api.get("/compliance/alerts"),
      ]);
      setRecipients(r.data.recipients || []);
      setIncidents(i.data.incidents || []);
      setChecklist(c.data.items || []);
      setAlerts(a.data);
      setError(null);
    } catch (err) {
      if (err?.response?.status === 403) {
        setError("This dashboard is for the data controller (owner) only.");
      } else {
        setError("Could not load compliance data.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const summary = useMemo(() => {
    const green = recipients.filter((r) => r.status === "green").length;
    const amber = recipients.filter((r) => r.status === "amber").length;
    const red = recipients.filter((r) => r.status === "red").length;
    return { green, amber, red };
  }, [recipients]);

  if (error) {
    return (
      <AppLayout>
        <div className="max-w-3xl mx-auto p-6">
          <div className="brutal-card p-6 bg-rose-50" data-testid="compliance-error">
            <h2 className="font-display font-black text-2xl mb-2">Access restricted</h2>
            <p className="text-sm text-slate-700">{error}</p>
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="max-w-7xl mx-auto p-4 md:p-6 space-y-6" data-testid="compliance-page">
        {/* Header */}
        <header className="brutal-card p-5 bg-butter">
          <div className="flex items-center gap-3 mb-2">
            <ShieldCheck size={28} weight="fill" />
            <div>
              <div className="text-xs uppercase tracking-widest font-bold text-slate-700">UK GDPR</div>
              <h1 className="font-display font-black text-3xl md:text-4xl">Compliance Dashboard</h1>
            </div>
          </div>
          <p className="text-sm text-slate-800 max-w-3xl">
            One place to track every US-based data recipient, the mechanism that keeps each transfer lawful, and any
            CLOUD Act exposure — with alerts when your DPF certifications are about to expire or your Transfer Risk
            Assessments go stale.
          </p>
          <div className="grid grid-cols-3 gap-2 mt-4 max-w-xl">
            <div className="rounded-md border-2 border-emerald-700 bg-emerald-100 p-2 text-center">
              <div className="text-[10px] uppercase tracking-widest font-bold text-emerald-900">DPF certified</div>
              <div className="font-display font-black text-2xl text-emerald-900" data-testid="summary-green">
                {summary.green}
              </div>
            </div>
            <div className="rounded-md border-2 border-amber-700 bg-amber-100 p-2 text-center">
              <div className="text-[10px] uppercase tracking-widest font-bold text-amber-900">IDTA only</div>
              <div className="font-display font-black text-2xl text-amber-900" data-testid="summary-amber">
                {summary.amber}
              </div>
            </div>
            <div className="rounded-md border-2 border-rose-700 bg-rose-100 p-2 text-center">
              <div className="text-[10px] uppercase tracking-widest font-bold text-rose-900">At risk</div>
              <div className="font-display font-black text-2xl text-rose-900" data-testid="summary-red">
                {summary.red}
              </div>
            </div>
          </div>
        </header>

        <AlertsBanner alerts={alerts} loading={loading} />

        {loading ? (
          <div className="brutal-card p-8 flex items-center justify-center gap-2 text-slate-600">
            <CircleNotch size={20} className="animate-spin" /> Loading…
          </div>
        ) : (
          <>
            <RecipientsSection recipients={recipients} refresh={loadAll} />
            <CloudActSection incidents={incidents} refresh={loadAll} />
            <ChecklistSection items={checklist} refresh={loadAll} />
          </>
        )}

        <footer className="text-xs text-slate-600 text-center py-2">
          Signed in as <span className="font-bold">{user?.email}</span> · Data on this page is stored in the
          controller-facing database and is <em>not</em> exposed to any US recipient.
        </footer>
      </div>
    </AppLayout>
  );
}
