import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "@/lib/api";
import GlobalNav from "@/components/GlobalNav";
import { CheckCircle, XCircle, Hourglass, GraduationCap } from "@phosphor-icons/react";

export default function BillingSuccess() {
  const [params] = useSearchParams();
  const session_id = params.get("session_id");
  const [status, setStatus] = useState("pending");
  const [tx, setTx] = useState(null);
  const attempts = useRef(0);

  useEffect(() => {
    if (!session_id) { setStatus("error"); return; }
    const poll = async () => {
      attempts.current += 1;
      try {
        const { data } = await api.get(`/billing/status/${session_id}`);
        setTx(data);
        if (data.payment_status === "paid") { setStatus("paid"); return; }
        if (data.status === "expired" || data.payment_status === "expired") { setStatus("expired"); return; }
        if (attempts.current >= 8) { setStatus("timeout"); return; }
        setTimeout(poll, 2000);
      } catch {
        if (attempts.current >= 8) { setStatus("error"); return; }
        setTimeout(poll, 2000);
      }
    };
    poll();
  }, [session_id]);

  return (
    <div className="min-h-screen bg-paper">
      <GlobalNav />
      <div className="flex items-center justify-center p-6 py-12">
        <div className="brutal-card p-10 max-w-lg w-full text-center" data-testid="billing-success-card">
        {status === "pending" && (
          <>
            <Hourglass size={48} weight="duotone" className="mx-auto mb-4" />
            <h1 className="font-display font-black text-3xl mb-2">Confirming your payment…</h1>
            <p className="text-[#4A4A4A]">This usually takes a few seconds.</p>
          </>
        )}
        {status === "paid" && (
          <>
            <CheckCircle size={56} weight="fill" className="mx-auto mb-4" />
            <h1 className="font-display font-black text-4xl mb-2">You're in.</h1>
            <p className="text-[#4A4A4A] mb-6">
              Your <span className="font-bold capitalize">{tx?.plan_id}</span> plan is active. Time to study.
            </p>
            <Link to="/dashboard" className="brutal-btn bg-ink text-white inline-block" data-testid="billing-go-dashboard">
              Go to dashboard
            </Link>
          </>
        )}
        {(status === "expired" || status === "timeout" || status === "error") && (
          <>
            <XCircle size={48} weight="fill" className="mx-auto mb-4 text-focus" />
            <h1 className="font-display font-black text-3xl mb-2">Hmm, that didn't go through.</h1>
            <p className="text-[#4A4A4A] mb-6">{status === "expired" ? "The checkout session expired." : "We couldn't confirm the payment in time. If you were charged, refresh in a moment."}</p>
            <Link to="/pricing" className="brutal-btn bg-ink text-white inline-block" data-testid="billing-try-again">Try again</Link>
          </>
        )}
        </div>
      </div>
    </div>
  );
}
