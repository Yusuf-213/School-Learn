import GlobalNav from "@/components/GlobalNav";
import { Link } from "react-router-dom";

export default function AppLayout({ children }) {
  return (
    <div className="min-h-screen bg-paper text-ink flex flex-col">
      <GlobalNav />
      <main className="flex-1 w-full max-w-7xl mx-auto px-4 md:px-6 py-8 md:py-10">
        {children}
      </main>
      <footer className="border-t-2 border-ink py-4 text-center text-xs text-[#4A4A4A]">
        <div className="space-x-4">
          <Link to="/safety" className="underline hover:text-ink" data-testid="footer-safety">Safety & safeguarding</Link>
          <Link to="/contact" className="underline hover:text-ink" data-testid="footer-contact">Contact</Link>
          <Link to="/mfa" className="underline hover:text-ink" data-testid="footer-mfa">Two-factor auth</Link>
        </div>
        <div className="mt-2">© {new Date().getFullYear()} Learnify · Built safe for UK schools.</div>
      </footer>
    </div>
  );
}
