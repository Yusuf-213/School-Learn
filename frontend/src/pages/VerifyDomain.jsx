import { useEffect, useRef, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { api } from "@/lib/api";
import GlobalNav from "@/components/GlobalNav";
import { ShieldCheck, XCircle, Envelope } from "@phosphor-icons/react";

export default function VerifyDomain() {
  const [params] = useSearchParams();
  const token = params.get("token");
  const [state, setState] = useState({ status: "loading" });
  const consumedRef = useRef(false);

  useEffect(() => {
    if (!token) { setState({ status: "error", detail: "Missing token" }); return; }
    // Guard against React StrictMode double-invocation burning a one-time token.
    if (consumedRef.current) return;
    consumedRef.current = true;
    api.get(`/auth/verify_domain?token=${encodeURIComponent(token)}`)
      .then(({ data }) => setState({ status: "ok", data }))
      .catch((e) => setState({ status: "error", detail: e?.response?.data?.detail || "Verification failed" }));
  }, [token]);

  return (
    <div className="min-h-screen bg-paper text-ink">
      <GlobalNav />
      <main className="max-w-lg mx-auto px-6 py-16">
        {state.status === "loading" && (
          <div className="brutal-card p-8 text-center" data-testid="verify-loading">
            <Envelope size={36} weight="duotone" className="mx-auto" />
            <p className="mt-4 text-sm text-[#4A4A4A]">Verifying your school's domain…</p>
          </div>
        )}
        {state.status === "ok" && (
          <div className="brutal-card p-8 bg-mint text-center" data-testid="verify-success">
            <ShieldCheck size={44} weight="fill" className="mx-auto text-green-800" />
            <h1 className="font-display font-black text-3xl mt-3">Domain verified.</h1>
            <p className="mt-3 text-sm">
              <b>{state.data.email}</b> is confirmed as the admin for your school on Learnify.
            </p>
            <Link to="/dashboard" className="brutal-btn bg-ink text-white inline-block mt-4" data-testid="verify-continue">
              Go to dashboard
            </Link>
          </div>
        )}
        {state.status === "error" && (
          <div className="brutal-card p-8 bg-peach text-center" data-testid="verify-error">
            <XCircle size={44} weight="fill" className="mx-auto text-red-800" />
            <h1 className="font-display font-black text-3xl mt-3">Link not valid.</h1>
            <p className="mt-3 text-sm">{state.detail}</p>
            <p className="mt-2 text-xs text-[#4A4A4A]">
              Ask your school admin to send you a fresh verification link.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
