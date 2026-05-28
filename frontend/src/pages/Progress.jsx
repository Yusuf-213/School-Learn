import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import { findSubject, findTopic } from "@/lib/subjects";
import { CheckCircle, ArrowRight, Trophy } from "@phosphor-icons/react";

export default function Progress() {
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState({ topics_started: 0, topics_completed: 0, focus_minutes: 0, focus_sessions_completed: 0 });

  useEffect(() => {
    (async () => {
      try {
        const [p, s] = await Promise.all([api.get("/progress"), api.get("/stats")]);
        setItems(p.data.items || []);
        setStats(s.data);
      } catch {}
    })();
  }, []);

  return (
    <AppLayout>
      <div className="max-w-5xl space-y-8">
        <div>
          <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2 text-[#4A4A4A]">Progress</div>
          <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tight">Your journey so far.</h1>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Stat label="Topics started" value={stats.topics_started} bg="bg-mint" />
          <Stat label="Topics completed" value={stats.topics_completed} bg="bg-butter" />
          <Stat label="Focus sessions" value={stats.focus_sessions_completed} bg="bg-lavender" />
          <Stat label="Focus minutes" value={stats.focus_minutes} bg="bg-peach" />
        </div>

        {items.length === 0 ? (
          <div className="brutal-card p-10 text-center">
            <Trophy size={36} weight="duotone" className="mx-auto mb-3" />
            <div className="font-display font-bold text-2xl">No progress yet.</div>
            <p className="text-[#4A4A4A] mt-2">Start a topic and your activity will show up here.</p>
            <Link to="/subjects" className="mt-6 inline-flex brutal-btn bg-ink text-white" data-testid="progress-empty-cta">Browse subjects</Link>
          </div>
        ) : (
          <div className="space-y-2">
            {items.map((p) => {
              const subject = findSubject(p.subject);
              const topic = findTopic(p.subject, p.topic);
              return (
                <Link
                  key={p.subject + p.topic}
                  to={`/subjects/${p.subject}/topic/${p.topic}`}
                  className="brutal-card p-5 flex items-center justify-between bg-white"
                  data-testid={`progress-row-${p.subject}-${p.topic}`}
                >
                  <div className="flex items-center gap-3">
                    {p.completed
                      ? <CheckCircle size={22} weight="fill" />
                      : <div className="w-[22px] h-[22px] border-2 border-ink rounded-full" />}
                    <div>
                      <div className="text-xs uppercase tracking-[0.2em] font-bold text-[#4A4A4A]">{subject?.name || p.subject}</div>
                      <div className="font-display font-bold text-lg">{topic?.name || p.topic}</div>
                    </div>
                  </div>
                  <ArrowRight size={20} weight="bold" />
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </AppLayout>
  );
}

function Stat({ label, value, bg }) {
  return (
    <div className={`brutal-card p-5 ${bg}`}>
      <div className="font-display font-black text-3xl">{value}</div>
      <div className="text-xs tracking-[0.2em] uppercase font-bold mt-1">{label}</div>
    </div>
  );
}
