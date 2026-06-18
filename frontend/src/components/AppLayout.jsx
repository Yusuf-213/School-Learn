import GlobalNav from "@/components/GlobalNav";

export default function AppLayout({ children }) {
  return (
    <div className="min-h-screen bg-paper text-ink flex flex-col">
      <GlobalNav />
      <main className="flex-1 w-full max-w-7xl mx-auto px-4 md:px-6 py-8 md:py-10">
        {children}
      </main>
      <footer className="border-t-2 border-ink py-4 text-center text-xs text-[#4A4A4A]">
        © {new Date().getFullYear()} Learnify · Built for serious learners.
      </footer>
    </div>
  );
}
