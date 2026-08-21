import AppLayout from "@/components/AppLayout";
import { Exam, CheckCircle, Clock } from "@phosphor-icons/react";

const UPCOMING = [
  { subject: "Maths", title: "Algebra unit test", due: "Fri 24 Feb", weight: "20%", status: "upcoming" },
  { subject: "English", title: "Essay: Themes in Macbeth", due: "Mon 27 Feb", weight: "15%", status: "upcoming" },
  { subject: "Science", title: "Photosynthesis lab report", due: "Wed 1 Mar", weight: "10%", status: "upcoming" },
];

const RESULTS = [
  { subject: "Maths", title: "Number & Place Value quiz", mark: "88%", grade: "A", date: "10 Feb" },
  { subject: "English", title: "Reading comprehension", mark: "76%", grade: "B", date: "07 Feb" },
];

export default function Assessments() {
  return (
    <AppLayout>
      <div className="space-y-6" data-testid="assessments-page">
        <header>
          <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2 text-[#4A4A4A] flex items-center gap-2">
            <Exam size={14} weight="fill" /> Assessments
          </div>
          <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tight">Assessments.</h1>
          <p className="text-[#4A4A4A] mt-3">Upcoming tests, coursework and past marks in one place.</p>
        </header>

        <section>
          <h2 className="font-display font-extrabold text-2xl mb-3 flex items-center gap-2">
            <Clock size={20} /> Upcoming
          </h2>
          <div className="space-y-2">
            {UPCOMING.map((a) => (
              <div key={a.title} className="brutal-card p-4 bg-white flex flex-wrap justify-between gap-3" data-testid={`assess-upcoming-${a.subject}`}>
                <div>
                  <div className="text-xs uppercase tracking-[0.2em] font-bold text-[#4A4A4A]">{a.subject}</div>
                  <div className="font-bold">{a.title}</div>
                </div>
                <div className="text-right text-sm">
                  <div>Due <b>{a.due}</b></div>
                  <div className="text-[#4A4A4A]">Weight {a.weight}</div>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section>
          <h2 className="font-display font-extrabold text-2xl mb-3 flex items-center gap-2">
            <CheckCircle size={20} /> Recent results
          </h2>
          <div className="overflow-x-auto brutal-card">
            <table className="min-w-full text-sm">
              <thead className="bg-mint border-b-2 border-ink">
                <tr>
                  <th className="text-left p-3 font-display">Subject</th>
                  <th className="text-left p-3 font-display">Title</th>
                  <th className="text-right p-3 font-display">Mark</th>
                  <th className="text-left p-3 font-display">Grade</th>
                  <th className="text-left p-3 font-display">Date</th>
                </tr>
              </thead>
              <tbody>
                {RESULTS.map((r) => (
                  <tr key={r.title} className="border-t border-ink/20" data-testid={`assess-result-${r.subject}`}>
                    <td className="p-3 font-bold">{r.subject}</td>
                    <td className="p-3">{r.title}</td>
                    <td className="p-3 text-right font-mono">{r.mark}</td>
                    <td className="p-3"><span className="px-2 py-0.5 border-2 border-ink rounded-md bg-butter text-xs font-bold">{r.grade}</span></td>
                    <td className="p-3 text-[#4A4A4A]">{r.date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </AppLayout>
  );
}
