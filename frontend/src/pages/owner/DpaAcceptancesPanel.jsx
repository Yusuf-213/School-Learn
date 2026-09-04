import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { DownloadSimple } from "@phosphor-icons/react";

export default function DpaAcceptancesPanel() {
  const [rows, setRows] = useState([]);
  const [reminders, setReminders] = useState(null);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const [a, r] = await Promise.all([
          api.get("/owner/dpa/acceptances"),
          api.get("/owner/dpa/reminders"),
        ]);
        setRows(a.data.acceptances || []);
        setReminders(r.data);
      } catch (e) {
        toast.error(e?.response?.data?.detail || "Could not load acceptances");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const filtered = q
    ? rows.filter((r) =>
        [r.email, r.school_name, r.doc_version, r.kind]
          .filter(Boolean).join(" ").toLowerCase().includes(q.toLowerCase())
      )
    : rows;

  const downloadCsv = async () => {
    try {
      const res = await api.get("/owner/dpa/acceptances.csv", { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: "text/csv" }));
      const a = document.createElement("a");
      const cd = res.headers["content-disposition"] || "";
      const m = cd.match(/filename="?([^"]+)"?/);
      a.href = url;
      a.download = m?.[1] || "learnify-dpa-acceptances.csv";
      document.body.appendChild(a); a.click(); a.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error("Export failed");
    }
  };

  return (
    <div className="space-y-4" data-testid="dpa-panel">
      {reminders && (reminders.counts.upcoming + reminders.counts.stale + reminders.counts.never > 0) && (
        <section className="brutal-card p-5 bg-peach" data-testid="dpa-reminders">
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div>
              <div className="text-xs uppercase tracking-[0.2em] font-bold">Renewal reminders</div>
              <h3 className="font-display font-bold text-lg">
                {reminders.counts.upcoming} due in 30 days · {reminders.counts.stale} on outdated DPA · {reminders.counts.never} never signed
              </h3>
              <p className="text-xs text-[#333] mt-1">Current DPA version: <b>{reminders.current_version}</b></p>
            </div>
          </div>
          <div className="mt-3 space-y-2 max-h-64 overflow-y-auto">
            {reminders.upcoming.map((u) => (
              <div key={"u-" + u.user_id} className="flex flex-wrap items-center gap-2 text-xs bg-white border-2 border-ink rounded-md p-2" data-testid={`reminder-upcoming-${u.user_id}`}>
                <span className="font-mono">{u.email}</span>
                <span className="text-[#4A4A4A]">·</span>
                <span>{u.role}</span>
                <span className="ml-auto font-bold">Renews in {u.days_until_renewal}d · {u.renewal_date}</span>
                <a href={`mailto:${u.email}?subject=Re-accept%20Learnify%20Privacy%20Policy%20%26%20DPA&body=Hi%20${encodeURIComponent(u.name || "")}%2C%0A%0AOur%20Privacy%20Policy%20and%20Data%20Processing%20Agreement%20is%20due%20for%20renewal%20on%20${u.renewal_date}.%20Please%20sign%20in%20to%20Learnify%20and%20re-accept%20the%20latest%20version%20so%20your%20audit%20trail%20stays%20current.%0A%0AThanks.`}
                  className="brutal-btn bg-ink text-white text-xs">Email</a>
              </div>
            ))}
            {reminders.stale.map((u) => (
              <div key={"s-" + u.user_id} className="flex flex-wrap items-center gap-2 text-xs bg-white border-2 border-ink rounded-md p-2" data-testid={`reminder-stale-${u.user_id}`}>
                <span className="font-mono">{u.email}</span>
                <span className="text-[#4A4A4A]">·</span>
                <span>{u.role}</span>
                <span className="ml-auto font-bold">On v{u.dpa_accepted_version} — needs v{u.current_version}</span>
                <a href={`mailto:${u.email}?subject=Please%20re-accept%20updated%20Privacy%20Policy%20%26%20DPA&body=Hi%20${encodeURIComponent(u.name || "")}%2C%0A%0AWe%27ve%20published%20version%20${u.current_version}%20of%20our%20Privacy%20Policy%20and%20DPA.%20Please%20sign%20in%20to%20Learnify%20and%20accept%20the%20new%20version.`}
                  className="brutal-btn bg-ink text-white text-xs">Email</a>
              </div>
            ))}
            {reminders.never_accepted.map((u) => (
              <div key={"n-" + u.user_id} className="flex flex-wrap items-center gap-2 text-xs bg-white border-2 border-ink rounded-md p-2" data-testid={`reminder-never-${u.user_id}`}>
                <span className="font-mono">{u.email}</span>
                <span className="text-[#4A4A4A]">·</span>
                <span>{u.role}</span>
                <span className="ml-auto font-bold text-red-800">Never signed</span>
              </div>
            ))}
          </div>
        </section>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Filter by email, school, version…"
          className="brutal-input flex-1 min-w-[220px]"
          data-testid="dpa-filter"
        />
        <button onClick={downloadCsv}
          className="brutal-btn bg-mint hover:bg-white inline-flex items-center gap-2"
          data-testid="dpa-export-csv">
          <DownloadSimple size={16} weight="bold" /> Export CSV
        </button>
      </div>

      {loading ? (
        <div className="brutal-card p-6 text-[#4A4A4A]">Loading…</div>
      ) : (
        <div className="overflow-x-auto brutal-card">
          <table className="min-w-full text-sm">
            <thead className="bg-lavender border-b-2 border-ink">
              <tr>
                <th className="text-left p-3 font-display">When</th>
                <th className="text-left p-3 font-display">Email</th>
                <th className="text-left p-3 font-display">School</th>
                <th className="text-left p-3 font-display">Version</th>
                <th className="text-left p-3 font-display">Kind</th>
                <th className="text-left p-3 font-display">Signature</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((r) => (
                <tr key={r.acceptance_id} className="border-t border-ink/20" data-testid={`dpa-row-${r.acceptance_id}`}>
                  <td className="p-3 text-xs text-[#4A4A4A] whitespace-nowrap">{new Date(r.accepted_at).toLocaleString()}</td>
                  <td className="p-3 font-mono text-xs">{r.email}</td>
                  <td className="p-3">{r.school_name || "—"}</td>
                  <td className="p-3">{r.doc_version || "—"}</td>
                  <td className="p-3">
                    <span className={`px-2 py-0.5 border-2 border-ink rounded-md text-xs font-bold ${r.kind === "signed_pdf_download" ? "bg-butter" : "bg-mint"}`}>
                      {r.kind || "accept"}
                    </span>
                  </td>
                  <td className="p-3 font-mono text-xs break-all">{(r.signature_sha256 || "").slice(0, 16)}…</td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={6} className="p-6 text-center text-[#4A4A4A]">No acceptances match.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
