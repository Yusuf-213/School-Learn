import AppLayout from "@/components/AppLayout";
import { FileText, DownloadSimple } from "@phosphor-icons/react";
import { toast } from "sonner";

const REPORTS = [
  { title: "Term 1 progress report", period: "Autumn 2025", subjects: 8, average: "B+", available: true },
  { title: "Term 2 progress report", period: "Spring 2026", subjects: 8, average: "—", available: false },
  { title: "End-of-year summary", period: "2025/26", subjects: 8, average: "—", available: false },
];

function downloadReport(r) {
  if (!r.available) {
    toast.info(`${r.title} is not published yet — check back at the end of term.`);
    return;
  }
  // Simple client-side text stub so the button is functional today; real PDF sync coming next term.
  const body = `Learnify · ${r.title}\nPeriod: ${r.period}\nSubjects: ${r.subjects}\nOverall grade: ${r.average}\n\n(Full termly report will be attached here once your teachers publish it.)`;
  const blob = new Blob([body], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = `${r.title.replace(/\s+/g, "-")}.txt`;
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
  toast.success("Report downloaded");
}

export default function Reports() {
  return (
    <AppLayout>
      <div className="space-y-6" data-testid="reports-page">
        <header>
          <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2 text-[#4A4A4A] flex items-center gap-2">
            <FileText size={14} weight="fill" /> Reports
          </div>
          <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tight">Reports.</h1>
          <p className="text-[#4A4A4A] mt-3">Termly summaries you can share with parents or upload to SIMS.</p>
        </header>

        <div className="space-y-3">
          {REPORTS.map((r) => (
            <div key={r.title} className="brutal-card p-5 bg-white flex flex-wrap items-center justify-between gap-3" data-testid={`report-${r.period}`}>
              <div>
                <div className="text-xs uppercase tracking-[0.2em] font-bold text-[#4A4A4A]">{r.period}</div>
                <h3 className="font-display font-bold text-lg mt-1">{r.title}</h3>
                <p className="text-xs text-[#4A4A4A] mt-1">{r.subjects} subjects · Average: {r.average}</p>
              </div>
              <button
                onClick={() => downloadReport(r)}
                className={`brutal-btn inline-flex items-center gap-2 ${r.available ? "bg-mint hover:bg-white" : "bg-white"}`}
                data-testid={`report-download-${r.period}`}
              >
                <DownloadSimple size={16} weight="bold" />
                {r.available ? "Download report" : "Notify when ready"}
              </button>
            </div>
          ))}
        </div>
      </div>
    </AppLayout>
  );
}
