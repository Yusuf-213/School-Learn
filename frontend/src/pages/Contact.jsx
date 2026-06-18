import GlobalNav from "@/components/GlobalNav";
import { EnvelopeSimple, ShieldCheck, Buildings, ChatCircle } from "@phosphor-icons/react";

export default function Contact() {
  return (
    <div className="min-h-screen bg-paper">
      <GlobalNav />
      <main className="max-w-3xl mx-auto px-6 py-10 space-y-6" data-testid="contact-page">
        <div>
          <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2 text-[#4A4A4A]">Contact</div>
          <h1 className="font-display font-black text-4xl tracking-tight">Get in touch.</h1>
        </div>

        <div className="brutal-card p-6 bg-mint">
          <ShieldCheck size={24} weight="duotone" />
          <h2 className="font-display font-bold text-xl mt-2">Safeguarding</h2>
          <p className="text-sm text-[#4A4A4A] mt-1">For urgent safeguarding concerns relating to a Learnify user.</p>
          <p className="mt-2 text-sm"><EnvelopeSimple size={14} className="inline mr-1" /> <a className="underline" href="mailto:safeguarding@learnify.app">safeguarding@learnify.app</a></p>
        </div>

        <div className="brutal-card p-6 bg-butter">
          <Buildings size={24} weight="duotone" />
          <h2 className="font-display font-bold text-xl mt-2">Schools & sales</h2>
          <p className="text-sm text-[#4A4A4A] mt-1">Register your school via the in-app flow, or email us if you'd like an invoiced quote.</p>
          <p className="mt-2 text-sm"><EnvelopeSimple size={14} className="inline mr-1" /> <a className="underline" href="mailto:schools@learnify.app">schools@learnify.app</a></p>
        </div>

        <div className="brutal-card p-6 bg-white">
          <ChatCircle size={24} weight="duotone" />
          <h2 className="font-display font-bold text-xl mt-2">Support</h2>
          <p className="text-sm text-[#4A4A4A] mt-1">Bugs, feature requests, or anything else.</p>
          <p className="mt-2 text-sm"><EnvelopeSimple size={14} className="inline mr-1" /> <a className="underline" href="mailto:support@learnify.app">support@learnify.app</a></p>
        </div>

        <div className="brutal-card p-6 bg-lavender">
          <h2 className="font-display font-bold text-xl">Data protection (UK GDPR)</h2>
          <p className="text-sm text-[#4A4A4A] mt-1">Data Protection Officer:</p>
          <p className="mt-2 text-sm"><EnvelopeSimple size={14} className="inline mr-1" /> <a className="underline" href="mailto:dpo@learnify.app">dpo@learnify.app</a></p>
        </div>
      </main>
    </div>
  );
}
