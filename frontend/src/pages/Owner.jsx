import { useEffect, useState } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Buildings, Users, BookOpen, Lightning, ChartLineUp, Chat, Crown } from "@phosphor-icons/react";

export default function Owner() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [schools, setSchools] = useState([]);
  const [suggestions, setSuggestions] = useState([]);

  useEffect(() => {
    (async () => {
      try {
        const [s, sc, sg] = await Promise.all([
          api.get("/owner/stats"),
          api.get("/owner/schools"),
          api.get("/owner/suggestions"),
        ]);
        setStats(s.data);
        setSchools(sc.data.schools);
        setSuggestions(sg.data.items);
      } catch {}
    })();
  }, []);

  if (user?.role !== "owner") {
    return (
      <AppLayout>
        <div className="brutal-card p-8 max-w-md mx-auto">
          <Crown size={36} weight="duotone" />
          <h1 className="font-display font-black text-2xl mt-3">Owner panel</h1>
          <p className="text-[#4A4A4A] mt-2">Only the owner account can access this page.</p>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="space-y-8" data-testid="owner-page">
        <div>
          <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2 text-[#4A4A4A]">Owner panel</div>
          <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tight">Learnify HQ.</h1>
          <p className="text-[#4A4A4A] mt-3">Everything across every school, in one view.</p>
        </div>

        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Stat label="Schools" value={stats.schools} icon={Buildings} bg="bg-mint" tid="stat-schools" />
            <Stat label="Paying schools" value={stats.paying_schools} icon={Crown} bg="bg-butter" tid="stat-paying" />
            <Stat label="Students" value={stats.students} icon={Users} bg="bg-lavender" tid="stat-students" />
            <Stat label="Teachers" value={stats.teachers} icon={Users} bg="bg-peach" tid="stat-teachers" />
            <Stat label="Homework set" value={stats.homework} icon={BookOpen} bg="bg-white" tid="stat-homework" />
            <Stat label="Lessons planned" value={stats.lessons} icon={Lightning} bg="bg-white" tid="stat-lessons" />
            <Stat label="Dreams logged" value={stats.dreams} icon={ChartLineUp} bg="bg-white" tid="stat-dreams" />
            <Stat label="Suggestions" value={stats.suggestions} icon={Chat} bg="bg-white" tid="stat-suggestions" />
          </div>
        )}

        <section>
          <h2 className="font-display font-extrabold text-2xl tracking-tight mb-4">Schools</h2>
          {schools.length === 0 ? (
            <div className="brutal-card p-6 text-[#4A4A4A]">No schools have registered yet.</div>
          ) : (
            <div className="overflow-x-auto brutal-card">
              <table className="min-w-full text-sm">
                <thead className="bg-butter border-b-2 border-ink">
                  <tr>
                    <th className="text-left p-3 font-display">School</th>
                    <th className="text-left p-3 font-display">Domain</th>
                    <th className="text-left p-3 font-display">Plan</th>
                    <th className="text-right p-3 font-display">Students</th>
                    <th className="text-right p-3 font-display">Teachers</th>
                    <th className="text-right p-3 font-display">Classes</th>
                    <th className="text-right p-3 font-display">Homework</th>
                    <th className="text-left p-3 font-display">Joined</th>
                  </tr>
                </thead>
                <tbody>
                  {schools.map((s) => (
                    <tr key={s.school_id} className="border-t border-ink/20" data-testid={`owner-school-${s.school_id}`}>
                      <td className="p-3 font-bold">{s.name}</td>
                      <td className="p-3 text-[#4A4A4A]">@{s.email_domain}</td>
                      <td className="p-3">
                        <span className="px-2 py-0.5 border-2 border-ink rounded-md bg-mint text-xs font-bold uppercase">{s.subscription_tier || "free"}</span>
                      </td>
                      <td className="p-3 text-right font-mono">{s.student_count}</td>
                      <td className="p-3 text-right font-mono">{s.teacher_count}</td>
                      <td className="p-3 text-right font-mono">{s.classes_count}</td>
                      <td className="p-3 text-right font-mono">{s.homework_count}</td>
                      <td className="p-3 text-[#4A4A4A] text-xs">{new Date(s.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section>
          <h2 className="font-display font-extrabold text-2xl tracking-tight mb-4">Recent suggestions</h2>
          {suggestions.length === 0 ? (
            <div className="brutal-card p-6 text-[#4A4A4A]">Nothing in the inbox yet.</div>
          ) : (
            <div className="space-y-2">
              {suggestions.slice(0, 20).map((s) => (
                <div key={s.suggestion_id} className="brutal-card p-4 bg-white" data-testid={`owner-suggestion-${s.suggestion_id}`}>
                  <div className="flex justify-between items-start gap-3">
                    <div>
                      <div className="text-xs uppercase tracking-[0.2em] font-bold text-[#4A4A4A]">{s.category}</div>
                      <div className="text-sm mt-1">{s.message}</div>
                    </div>
                    <div className="text-xs text-[#4A4A4A]">{s.user_name || s.user_email}<br />{new Date(s.created_at).toLocaleDateString()}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </AppLayout>
  );
}

function Stat({ label, value, icon: Icon, bg, tid }) {
  return (
    <div className={`brutal-card p-4 ${bg}`} data-testid={tid}>
      <div className="flex items-center justify-between mb-2">
        <Icon size={18} weight="duotone" />
      </div>
      <div className="font-display font-black text-2xl">{value}</div>
      <div className="text-xs tracking-[0.2em] uppercase font-bold mt-1">{label}</div>
    </div>
  );
}
