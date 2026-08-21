import AppLayout from "@/components/AppLayout";
import { Megaphone, PushPin } from "@phosphor-icons/react";

const POSTS = [
  { pinned: true, from: "Head Teacher", when: "Today", title: "Half-term reminder", body: "School closes Friday for half term and reopens Monday 27 February. Have a great break." },
  { pinned: false, from: "Mr Ahmed · Maths", when: "Yesterday", title: "Algebra unit test on Friday", body: "Please make sure you've completed the practice sheet on Learnify before Friday's test." },
  { pinned: false, from: "Ms Patel · English", when: "2 days ago", title: "Book club sign-up open", body: "Sign up in the library for our Year 8 book club — first meet is next Tuesday." },
];

export default function Announcements() {
  return (
    <AppLayout>
      <div className="space-y-6" data-testid="announcements-page">
        <header>
          <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2 text-[#4A4A4A] flex items-center gap-2">
            <Megaphone size={14} weight="fill" /> Announcements
          </div>
          <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tight">Announcements.</h1>
          <p className="text-[#4A4A4A] mt-3">Everything the school wants pupils and staff to see this week.</p>
        </header>

        <div className="space-y-3">
          {POSTS.map((p) => (
            <div key={p.title} className={`brutal-card p-5 ${p.pinned ? "bg-butter" : "bg-white"}`} data-testid={`announcement-${p.title.slice(0, 8)}`}>
              <div className="flex items-start gap-3">
                {p.pinned && <PushPin size={18} weight="fill" className="mt-1" />}
                <div className="flex-1">
                  <div className="text-xs uppercase tracking-[0.2em] font-bold text-[#4A4A4A]">{p.from} · {p.when}</div>
                  <h3 className="font-display font-bold text-lg mt-1">{p.title}</h3>
                  <p className="text-sm mt-1">{p.body}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </AppLayout>
  );
}
