import AppLayout from "@/components/AppLayout";
import { CalendarBlank, Clock } from "@phosphor-icons/react";

const PERIODS = [
  { time: "08:45", subject: "Registration" },
  { time: "09:00", subject: "Maths" },
  { time: "10:00", subject: "English" },
  { time: "11:15", subject: "Break" },
  { time: "11:30", subject: "Science" },
  { time: "12:30", subject: "Lunch" },
  { time: "13:30", subject: "History" },
  { time: "14:30", subject: "PE" },
  { time: "15:30", subject: "End of day" },
];

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"];

export default function Timetable() {
  return (
    <AppLayout>
      <div className="space-y-6" data-testid="timetable-page">
        <header>
          <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2 text-[#4A4A4A] flex items-center gap-2">
            <CalendarBlank size={14} weight="fill" /> Weekly timetable
          </div>
          <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tight">Timetable.</h1>
          <p className="text-[#4A4A4A] mt-3">A quick view of the school week.</p>
        </header>

        <div className="overflow-x-auto brutal-card">
          <table className="min-w-full text-sm">
            <thead className="bg-butter border-b-2 border-ink">
              <tr>
                <th className="text-left p-3 font-display w-24"><Clock size={14} className="inline mr-1" /> Time</th>
                {DAYS.map((d) => (
                  <th key={d} className="text-left p-3 font-display">{d}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {PERIODS.map((p) => (
                <tr key={p.time} className="border-t border-ink/20" data-testid={`timetable-row-${p.time}`}>
                  <td className="p-3 font-mono font-bold whitespace-nowrap">{p.time}</td>
                  {DAYS.map((d) => (
                    <td key={d} className="p-3">
                      <span className={`inline-block px-2 py-1 rounded border-2 border-ink text-xs font-bold
                        ${p.subject === "Break" || p.subject === "Lunch" ? "bg-peach" : p.subject === "Registration" || p.subject === "End of day" ? "bg-mint" : "bg-white"}`}>
                        {p.subject}
                      </span>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="text-xs text-[#4A4A4A]">Sample timetable. Live timetable sync is coming next term.</p>
      </div>
    </AppLayout>
  );
}
