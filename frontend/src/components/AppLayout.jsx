import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import GlobalNav from "@/components/GlobalNav";
import SideNav, { SideNavMobileTrigger } from "@/components/SideNav";

export default function AppLayout({ children }) {
  const { user } = useAuth();
  const [mobileNav, setMobileNav] = useState(false);

  // Public pages keep the top nav only.
  if (!user) {
    return (
      <div className="min-h-screen bg-paper text-ink flex flex-col">
        <GlobalNav />
        <main className="flex-1 w-full max-w-7xl mx-auto px-4 md:px-6 py-8 md:py-10">
          {children}
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-paper text-ink flex">
      <SideNav mobileOpen={mobileNav} onMobileClose={() => setMobileNav(false)} />
      <div className="flex-1 flex flex-col min-w-0">
        <div className="lg:hidden sticky top-0 z-30 bg-paper/95 backdrop-blur border-b-2 border-ink px-4 py-3 flex items-center gap-3">
          <SideNavMobileTrigger onOpen={() => setMobileNav(true)} />
          <span className="font-display font-black text-lg tracking-tight">Learnify</span>
        </div>
        <main className="flex-1 w-full max-w-6xl mx-auto px-4 md:px-8 py-6 md:py-10" data-testid="app-main">
          {children}
        </main>
        <Footer />
      </div>
    </div>
  );
}

function Footer() {
  return (
    <footer className="border-t-2 border-ink py-4 text-center text-xs text-[#4A4A4A]">
      <div className="space-x-4">
        <Link to="/safety" className="underline hover:text-ink" data-testid="footer-safety">Safety & safeguarding</Link>
        <Link to="/dpa" className="underline hover:text-ink" data-testid="footer-dpa">Privacy & DPA</Link>
        <Link to="/contact" className="underline hover:text-ink" data-testid="footer-contact">Contact</Link>
        <Link to="/mfa" className="underline hover:text-ink" data-testid="footer-mfa">Two-factor auth</Link>
      </div>
      <div className="mt-2">© {new Date().getFullYear()} Learnify · Built safe for UK schools.</div>
    </footer>
  );
}
