import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { ShieldCheck, MagnifyingGlass, DownloadSimple } from "@phosphor-icons/react";

const ACTION_BG = {
  approved: "bg-mint",
  rejected: "bg-peach",
  created: "bg-butter",
};

export default function GuardianAuditPanel() {
  const [rows, setRows] = useState([]);
  const [q, setQ] = useState("");
  const [action, setAction] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (q) params.q = q;
      if (action) params.action = action;
      const { data } = await api.get("/parent-link-audit", { params });
      setRows(data.rows || []);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not load audit log");
    } finally {
      setLoading(false);
    }
  }, [q, action]);

  useEffect(() => { load(); }, [load]);

  const exportCsv = () => {
    const header = ["at", "action", "parent_email", "child_email", "actor_email", "actor_role", "note"];
    const csv = [header.join(",")]
      .concat(rows.map((r) => header.map((h) => JSON.stringify(r[h] ?? "")).join(",")))
      .join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `learnify-guardian-audit-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4" data-testid="guardian-audit-panel">
      <div className="brutal-card p-4 bg-lavender flex items-start gap-3">
        <ShieldCheck size={22} weight="fill" />
        <div>
          <div className="font-display font-bold text-lg">Guardian access — audit trail</div>
          <p className="text-sm text-[#333]">Every parent-link request and decision is stamped here. Search by email or filter by action for safeguarding queries.</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 items-center">
        <div className="relative flex-1 min-w-[220px]">
          <MagnifyingGlass size={14} weight="bold" className="absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            value={q} onChange={(e) => setQ(e.target.value)}
            placeholder="Search parent, child or reviewer email…"
            className="brutal-input w-full pl-9"
            data-testid="audit-search"
          />
        </div>
        <select value={action} onChange={(e) => setAction(e.target.value)}
          className="brutal-input" data-testid="audit-action-filter">
          <option value="">All actions</option>
          <option value="created">Requested</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
        </select>
        <button onClick={exportCsv} className="brutal-btn bg-mint hover:bg-white inline-flex items-center gap-2"
          data-testid="audit-export-csv">
          <DownloadSimple size={14} weight="bold" /> Export CSV
        </button>
      </div>

      {loading ? (
        <div className="brutal-card p-6 text-[#4A4A4A]">Loading…</div>
      ) : rows.length === 0 ? (
        <div className="brutal-card p-6 text-[#4A4A4A]" data-testid="audit-empty">No audit rows match this filter.</div>
      ) : (
        <div className="overflow-x-auto brutal-card">
          <table className="min-w-full text-sm">
            <thead className="bg-butter border-b-2 border-ink">
              <tr>
                <th className="text-left p-3 font-display">When</th>
                <th className="text-left p-3 font-display">Action</th>
                <th className="text-left p-3 font-display">Parent</th>
                <th className="text-left p-3 font-display">Child</th>
                <th className="text-left p-3 font-display">Reviewer</th>
                <th className="text-left p-3 font-display">Reason</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.audit_id} className="border-t border-ink/20" data-testid={`audit-row-${r.audit_id}`}>
                  <td className="p-3 text-xs text-[#4A4A4A] whitespace-nowrap">{new Date(r.at).toLocaleString()}</td>
                  <td className="p-3">
                    <span className={`px-2 py-0.5 border-2 border-ink rounded-md text-xs font-bold uppercase ${ACTION_BG[r.action] || "bg-white"}`}>
                      {r.action}
                    </span>
                  </td>
                  <td className="p-3 font-mono text-xs">{r.parent_email}</td>
                  <td className="p-3 font-mono text-xs">{r.child_email}</td>
                  <td className="p-3 font-mono text-xs">
                    {r.actor_email}
                    <div className="text-[10px] uppercase font-bold text-[#4A4A4A]">{r.actor_role || "—"}</div>
                  </td>
                  <td className="p-3 text-xs">{r.note || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
