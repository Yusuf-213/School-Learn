import AppLayout from "@/components/AppLayout";
import { ShieldCheck, EnvelopeSimple, Scales, Globe, Clock, UsersThree, Warning } from "@phosphor-icons/react";

function Section({ icon: Icon, title, children, tone = "bg-white", testId }) {
  return (
    <section className={`brutal-card p-6 ${tone}`} data-testid={testId}>
      <div className="flex items-center gap-2 mb-3">
        {Icon && <Icon size={20} weight="bold" />}
        <h2 className="font-display font-bold text-2xl">{title}</h2>
      </div>
      <div className="text-sm leading-relaxed text-[#333] space-y-3">{children}</div>
    </section>
  );
}

export default function Privacy() {
  return (
    <AppLayout>
      <div className="space-y-8" data-testid="privacy-page">
        <header>
          <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2 text-[#4A4A4A] flex items-center gap-2">
            <ShieldCheck size={14} weight="fill" /> Privacy
          </div>
          <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tight">
            Learnify customer privacy notice
          </h1>
          <p className="text-[#4A4A4A] mt-3 max-w-2xl">
            This privacy notice tells you what to expect us to do with your personal information.
          </p>
        </header>

        <Section icon={EnvelopeSimple} title="Contact details" tone="bg-mint" testId="privacy-contact">
          <p>
            Email:{" "}
            <a href="mailto:schoollearnsupport@pm.me" className="underline font-bold" data-testid="privacy-contact-email">
              schoollearnsupport@pm.me
            </a>
          </p>
        </Section>

        <Section title="What information we collect, use, and why" testId="privacy-what">
          <p className="font-bold">We collect or use the following information for student education and welfare:</p>
          <ul className="list-disc pl-5 space-y-1">
            <li>Names and contact details for students/children</li>
            <li>Names and contact details for parents, guardians, carers</li>
            <li>Date of birth</li>
            <li>Account access information</li>
            <li>Exam results and qualifications</li>
            <li>Progress reports</li>
          </ul>

          <p className="font-bold pt-2">
            We collect or use the following personal information for dealing with queries, complaints or claims:
          </p>
          <ul className="list-disc pl-5 space-y-1">
            <li>Names and contact details</li>
            <li>Account login or user information</li>
            <li>Purchase or service history</li>
            <li>Correspondence</li>
          </ul>

          <p className="font-bold pt-2">We collect or use the following information to comply with legal requirements:</p>
          <ul className="list-disc pl-5 space-y-1">
            <li>Any other personal information required to comply with legal obligations</li>
          </ul>
        </Section>

        <Section icon={Scales} title="Lawful bases and data protection rights" tone="bg-butter" testId="privacy-lawful">
          <p>
            Under UK data protection law, we must have a lawful basis for collecting and using your personal
            information.
          </p>
          <ul className="list-disc pl-5 space-y-1">
            <li>
              Our lawful bases for collecting or using personal information for{" "}
              <strong>student education and welfare</strong> are: Consent and Contract.
            </li>
            <li>
              Our lawful bases for collecting or using personal information for{" "}
              <strong>dealing with queries, complaints or claims</strong> are: Contract and Legitimate interests.
            </li>
            <li>
              Our lawful basis for collecting or using personal information to{" "}
              <strong>comply with legal requirements</strong> is: Legal obligation.
            </li>
          </ul>
          <p>
            Your data protection rights include: right of access, right to rectification, right to erasure, right to
            restriction of processing, right to object, right to data portability, and right to withdraw consent. We
            will respond to any request within one month.
          </p>
          <p>
            To make a data protection rights request, contact us at{" "}
            <a href="mailto:schoollearnsupport@pm.me" className="underline font-bold">
              schoollearnsupport@pm.me
            </a>
            .
          </p>
        </Section>

        <Section title="Where we get personal information from" testId="privacy-sources">
          <ul className="list-disc pl-5 space-y-1">
            <li>Directly from you</li>
            <li>Parents or carers</li>
          </ul>
        </Section>

        <Section icon={Clock} title="How long we keep information" testId="privacy-retention">
          <p>
            Personal data is retained for the duration of the school's active subscription plus 12 months, after which
            it is securely deleted. Financial transaction records are retained for 7 years in line with UK legal
            requirements. For our full retention schedule, see school-learn.com/privacy.
          </p>
        </Section>

        <Section icon={UsersThree} title="Who we share information with" testId="privacy-sharing">
          <ul className="list-disc pl-5 space-y-1">
            <li>Suppliers and service providers (including Stripe for payment processing)</li>
            <li>Cloud infrastructure providers hosting the application</li>
          </ul>
        </Section>

        <Section icon={Globe} title="Sharing information outside the UK" testId="privacy-international">
          <p>
            Where necessary, we transfer personal information outside of the UK. When doing so, we comply with UK GDPR,
            ensuring appropriate safeguards are in place.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse mt-2">
              <thead>
                <tr className="text-left border-b-2 border-ink">
                  <th className="py-2 pr-3 font-bold">Organisation</th>
                  <th className="py-2 pr-3 font-bold">Category</th>
                  <th className="py-2 pr-3 font-bold">Country</th>
                  <th className="py-2 font-bold">Mechanism</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-ink/20">
                  <td className="py-2 pr-3">Stripe</td>
                  <td className="py-2 pr-3">Payment processor</td>
                  <td className="py-2 pr-3">United States</td>
                  <td className="py-2">International Data Transfer Agreement (IDTA)</td>
                </tr>
                <tr>
                  <td className="py-2 pr-3">Emergent (cloud hosting provider)</td>
                  <td className="py-2 pr-3">Cloud infrastructure</td>
                  <td className="py-2 pr-3">United States</td>
                  <td className="py-2">International Data Transfer Agreement (IDTA)</td>
                </tr>
              </tbody>
            </table>
          </div>
        </Section>

        <Section icon={Warning} title="How to complain" tone="bg-mint" testId="privacy-complain">
          <p>
            Email:{" "}
            <a href="mailto:schoollearnsupport@pm.me" className="underline font-bold">
              schoollearnsupport@pm.me
            </a>
          </p>
          <p>
            If you remain unhappy after raising a complaint with us, you can complain to the ICO:
          </p>
          <div className="not-italic">
            <p className="font-bold">ICO Head Office</p>
            <p>4th Floor, No.3 Circle Square, 5 Hawkshaw Street, Manchester, M1 7BL</p>
            <p>Helpline: 0303 123 1113</p>
            <p>
              Website:{" "}
              <a
                href="https://www.ico.org.uk/make-a-complaint"
                target="_blank"
                rel="noopener noreferrer"
                className="underline font-bold"
              >
                https://www.ico.org.uk/make-a-complaint
              </a>
            </p>
          </div>
        </Section>
      </div>
    </AppLayout>
  );
}
