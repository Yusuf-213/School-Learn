import { useEffect, useMemo, useState } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import { toast } from "sonner";
import {
  GraduationCap, Warning, CheckCircle, Circle, Brain, PiggyBank, Receipt,
  FileText, Vault, ChartLine, TrendUp, Briefcase, Heart, ListChecks,
} from "@phosphor-icons/react";

const SubHead = ({ children }) => (
  <div className="text-xs uppercase tracking-[0.2em] font-bold text-[#4A4A4A] mt-4 mb-1">{children}</div>
);
const Bullets = ({ items }) => (
  <ul className="space-y-2 list-none">
    {items.map((it, i) => (
      <li key={i} className="flex gap-2">
        <span className="shrink-0 w-1.5 h-1.5 rounded-full bg-ink inline-block" style={{ marginTop: 8 }} />
        <span>{it}</span>
      </li>
    ))}
  </ul>
);

const SECTIONS = [
  {
    key: "mindset", title: "1. The mindset that sits under everything", icon: Brain,
    body: (
      <div className="space-y-3">
        <p>Success is mostly boring behaviour repeated for a long time. Spend less than you earn, invest the gap, keep learning, look after your health, and avoid big mistakes.</p>
        <p><strong>Compounding is the central idea.</strong> Growth earns growth. £200 a month for 30 years at an illustrative 7% a year <em>(not guaranteed)</em> grows to roughly <strong>£240,000</strong>, from only <strong>£72,000</strong> paid in. Most of that comes in the last decade, so starting early matters more than starting big.</p>
        <p><strong>Protect the downside first.</strong> You don't need home runs. You need to avoid the mistakes that wipe you out: high-interest debt, scams, putting everything into one bet, and having no safety net.</p>
        <p>Your skills and earning power are your biggest asset when you're young. Adding £5,000 to your income is worth more than investing £100 well.</p>
      </div>
    ),
  },
  {
    key: "foundations", title: "2. Money foundations (do these before investing)", icon: PiggyBank,
    body: (
      <Bullets items={[
        <><strong>Know your numbers.</strong> Track income and spending for a few months. Anything you can't explain is where the leaks are.</>,
        <><strong>Pay yourself first.</strong> Set up a standing order for savings the day you're paid, so saving isn't left to willpower.</>,
        <><strong>Build an emergency fund</strong> of 3 to 6 months of essential spending in an easy-access account. It stops a car repair or job loss turning into debt.</>,
        <><strong>Kill expensive debt.</strong> Credit cards and overdrafts charging 20% or more guarantee a worse return than most investments can reliably beat, so clear them first. Cheap debt, like a low-rate mortgage, is a different matter.</>,
        <><strong>Protect your credit score.</strong> Pay on time and keep card usage low. A good score means cheaper mortgages and loans for decades.</>,
        <><strong>Get basic insurance where it matters,</strong> such as income protection, contents and travel. Skip gimmicky extras.</>,
      ]} />
    ),
  },
  {
    key: "tax", title: "3. How tax works", icon: Receipt,
    body: (
      <div className="space-y-2">
        <SubHead>Income tax</SubHead>
        <Bullets items={[
          "Income tax is progressive. Each slice of income is taxed at its own rate, so a pay rise never reduces your take-home pay overall.",
          <>The <strong>personal allowance is £12,570</strong>. You can earn up to that before paying income tax. Main thresholds are frozen until at least 2031.</>,
          <>The <strong>basic-rate band is £37,700</strong> of taxable income. Rates are 20% on that band, 40% above roughly £50,270, and 45% above £125,140.</>,
          "Scotland has different bands.",
        ]} />
        <div className="brutal-card bg-mint p-4 mt-2 text-sm">
          <strong>Worked example:</strong> on a £40,000 salary, the first £12,570 is tax-free. The remaining £27,430 is taxed at 20%, which is £5,486 of income tax. You pay 40% only on the part of your income above £50,270, never on the whole lot.
        </div>
        <SubHead>National Insurance and tax codes</SubHead>
        <Bullets items={[
          "National Insurance is a separate payroll tax that funds the state pension and benefits. It's taken alongside income tax, so check your payslip for both.",
          "Tax codes (like 1257L) tell your employer how much allowance to apply. If yours looks odd, check it, because wrong codes are common and fixable.",
        ]} />
        <SubHead>Taxes on investing</SubHead>
        <Bullets items={[
          <><strong>Dividend tax</strong> applies to income from shares held outside an ISA or pension. The allowance is £500. Rates are 10.75% for basic-rate and 35.75% for higher-rate taxpayers (higher than last year).</>,
          <><strong>Capital gains tax (CGT)</strong> applies when you sell something for more than you paid. The annual exempt amount is £3,000. Gains above that are taxed at 18% in the basic-rate band and 24% in the higher bands.</>,
          "Inheritance tax is a separate topic for later in life.",
        ]} />
        <SubHead>The big idea</SubHead>
        <p>Legally shrinking your tax bill (using allowances, ISAs and pensions) is <strong>tax planning</strong>. Hiding income is <strong>evasion</strong>, which is illegal. The first is simply good housekeeping.</p>
      </div>
    ),
  },
  {
    key: "selfassessment", title: "4. Tax returns (Self Assessment)", icon: FileText,
    body: (
      <div className="space-y-2">
        <p>Most employees on PAYE never file one. You may need to if you:</p>
        <Bullets items={[
          "are self-employed and earn above the trading allowance (£1,000),",
          "are a company director, or have rental income or significant untaxed income,",
          "have investment income or gains above the allowances,",
          "or earn above the high-income child benefit threshold.",
        ]} />
        <SubHead>How it works</SubHead>
        <Bullets items={[
          "The UK tax year runs 6 April to 5 April.",
          "Register with HMRC (by 5 October after the tax year ends if it's your first time), then file online by 31 January and pay what you owe by the same date. Paper returns are due earlier.",
          "You report income, then claim allowable expenses (costs wholly and exclusively for the business) and reliefs.",
          <>Many self-employed people pay <strong>payments on account</strong>, which are advance instalments towards next year's bill. This catches people out, so set aside <strong>25 to 30%</strong> of profits as you earn them.</>,
          "Keep records for at least five years. Late-filing penalties are automatic and escalate.",
          "Making Tax Digital for Income Tax is rolling out, which means digital record-keeping and quarterly updates for many self-employed people. Check gov.uk for whether and when it applies to you.",
          "If your situation is more than simple, an accountant often pays for themselves.",
        ]} />
      </div>
    ),
  },
  {
    key: "wrappers", title: "5. Tax-efficient wrappers: ISAs and pensions", icon: Vault,
    body: (
      <div className="space-y-2">
        <p>A wrapper is an account type. What matters is the tax treatment, not what's inside it.</p>
        <SubHead>ISAs (Individual Savings Accounts)</SubHead>
        <Bullets items={[
          "Savings and investments held in ISAs are exempt from income tax and capital gains tax.",
          <>The allowance is <strong>£20,000 for 2026/27</strong>, and you can split it across different types of ISA. It resets each 6 April and doesn't roll over.</>,
          <><strong>Cash ISA:</strong> savings interest, tax-free.</>,
          <><strong>Stocks &amp; Shares ISA:</strong> investments, with gains and dividends tax-free. You can usually withdraw whenever you like.</>,
          <><strong>Lifetime ISA:</strong> up to £4,000 a year for those who qualify, with a 25% government bonus for a first home or retirement at 60, but a penalty for other withdrawals.</>,
          <><strong>Innovative Finance ISA:</strong> peer-to-peer lending, higher risk.</>,
          <><strong>Junior ISA:</strong> £9,000 a year for a child.</>,
        ]} />
        <div className="brutal-card bg-butter p-4 mt-2 text-sm">
          <strong>Change coming:</strong> from the 2027/28 tax year the Cash ISA allowance drops to £12,000, though people over 65 keep the full £20,000. The Stocks &amp; Shares ISA allowance is unchanged.
        </div>
        <SubHead>Pensions</SubHead>
        <Bullets items={[
          "Money paid in gets tax relief, so £100 in a pension costs a basic-rate taxpayer about £80 net.",
          "Workplace auto-enrolment typically has a minimum of 8% of qualifying pay going in, with at least 3% from the employer. Never turn down employer matching, because it's free money.",
          "You generally can't access it until your late 50s (the minimum age is rising). Locking it away is the price of the tax break.",
        ]} />
        <SubHead>A common order of priority</SubHead>
        <ol className="list-decimal pl-5 space-y-1">
          <li>Emergency fund.</li>
          <li>Get any employer pension match.</li>
          <li>Clear expensive debt.</li>
          <li>Fill a Stocks &amp; Shares ISA, adding a Lifetime ISA if you're saving for a first home.</li>
          <li>Put extra into the pension.</li>
          <li>Invest outside wrappers only after that.</li>
        </ol>
      </div>
    ),
  },
  {
    key: "stocks", title: "6. How stocks actually work", icon: ChartLine,
    body: (
      <div className="space-y-2">
        <p>A share is a slice of ownership in a company. If the company grows its profits, your slice becomes more valuable. You make money two ways: the price rises (capital gain), and the company pays out part of its profit (dividends).</p>
        <p>Prices move on expectations about the future, not just today's results. That's why prices can fall on good news if people hoped for better.</p>
        <Bullets items={[
          "A stock market is a place where buyers and sellers agree prices. If more people want to buy than sell, the price rises.",
          "An index (like the FTSE 100 or S&P 500) is a basket of companies used to measure a market.",
        ]} />
        <SubHead>Other asset types</SubHead>
        <Bullets items={[
          <><strong>Bonds:</strong> loans to governments or companies that pay interest. Usually steadier but lower-returning.</>,
          <><strong>Cash:</strong> safe in nominal terms, but inflation quietly erodes it.</>,
          <><strong>Property:</strong> slower, less liquid, and needs a lot of capital.</>,
          <><strong>Funds:</strong> bundle many assets together.</>,
        ]} />
        <SubHead>Risk and return</SubHead>
        <p>Risk and return travel together. Over long periods, shares have historically beaten cash and bonds, but with big swings. Falls of 20 to 50% have happened repeatedly and recovered, though never on a schedule. Money you'll need within about five years shouldn't be in shares.</p>
      </div>
    ),
  },
  {
    key: "investing", title: "7. How to invest sensibly", icon: TrendUp,
    body: (
      <Bullets items={[
        <><strong>Diversify.</strong> Holding thousands of companies across countries means one failure can't sink you. A global index fund or ETF does this in a single purchase.</>,
        <><strong>Costs matter enormously.</strong> A 1% annual fee sounds small, but over 30 years it can eat a quarter or more of your final pot. Look at the fund's ongoing charge and the platform fee. Low-cost passive funds are often a sensible core.</>,
        <><strong>Time in the market beats timing the market.</strong> Nobody reliably predicts short-term moves, including professionals. Investing a fixed amount monthly (pound-cost averaging) removes the temptation to try.</>,
        <><strong>Match risk to your timeline.</strong> The longer you have, the more shares you can hold. As a goal gets close, shift towards safer assets.</>,
        <><strong>Don't panic-sell.</strong> The most damaging behaviour is selling after a crash. Check in on a schedule rather than daily.</>,
        <><strong>Avoid common traps:</strong> hot tips, day trading, crypto hype, anyone promising guaranteed returns, "finfluencers" with something to sell, and borrowing to invest. Check any firm on the FCA register. If it sounds too good to be true, it is.</>,
        <><strong>Know what's protected.</strong> The FSCS covers up to £120,000 per person per authorised bank, but it doesn't protect you from investments losing value.</>,
      ]} />
    ),
  },
  {
    key: "career", title: "8. Career and earning power", icon: Briefcase,
    body: (
      <Bullets items={[
        <><strong>Build skills that are valuable and scarce.</strong> Combine technical or specialist ability with communication. The people who can explain, persuade and ship tend to be paid most.</>,
        <><strong>Negotiate.</strong> Salary is usually the biggest financial lever you control. Ask, with evidence, and do it every time you change roles.</>,
        <><strong>Build a network through genuine help.</strong> Many opportunities never get advertised.</>,
        <><strong>Own your learning.</strong> Read widely, learn in public, and put yourself in rooms slightly above your level.</>,
        <><strong>Consider ownership.</strong> Equity, a side business or a product can scale in ways a salary can't, but it carries risk, so keep your day income stable while testing ideas.</>,
      ]} />
    ),
  },
  {
    key: "nonmoney", title: "9. The non-money parts of success", icon: Heart,
    body: (
      <Bullets items={[
        <><strong>Health first.</strong> Sleep, exercise, and not smoking or drinking heavily are worth more than any investment return.</>,
        <><strong>Relationships.</strong> The people you spend time with shape your habits and opportunities, and they matter for happiness.</>,
        <><strong>Habits and systems over motivation.</strong> Automate good decisions (direct debits, calendar blocks) so they don't depend on how you feel.</>,
        <><strong>Decision quality.</strong> Think in probabilities, accept being wrong, and learn from the results. Beware overconfidence, especially in markets.</>,
        <><strong>Define "enough".</strong> Chasing more with no target is a treadmill. Decide what a good life looks like and aim at that.</>,
      ]} />
    ),
  },
];

const CHECKLIST = [
  ["track", "Track spending for one month."],
  ["emergency", "Open an easy-access account and build up an emergency fund."],
  ["pension", "Check you're getting your full employer pension match."],
  ["debt", "Clear any high-interest debt."],
  ["isa", "Open a Stocks & Shares ISA, set a monthly direct debit into a low-cost global index fund, and leave it alone."],
  ["taxcode", "Learn the basics of your tax code and, if relevant, Self Assessment."],
  ["skill", "Invest in one skill that increases your income each year."],
];

const TOTAL = SECTIONS.length + 1; // 9 sections + the checklist

export default function LifeSkills() {
  const [completed, setCompleted] = useState([]);
  const [checklist, setChecklist] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/me/life-skills")
      .then(({ data }) => { setCompleted(data.completed || []); setChecklist(data.checklist || []); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const save = async (next) => {
    try { await api.patch("/me/life-skills", next); } catch { toast.error("Couldn't save progress"); }
  };

  const toggleSection = (key) => {
    const next = completed.includes(key) ? completed.filter((k) => k !== key) : [...completed, key];
    setCompleted(next);
    save({ completed: next });
  };

  const toggleChecklistItem = (key) => {
    const next = checklist.includes(key) ? checklist.filter((k) => k !== key) : [...checklist, key];
    setChecklist(next);
    save({ checklist: next });
  };

  const checklistDone = CHECKLIST.length > 0 && CHECKLIST.every(([k]) => checklist.includes(k));
  const doneCount = useMemo(
    () => SECTIONS.filter((s) => completed.includes(s.key)).length + (checklistDone ? 1 : 0),
    [completed, checklistDone]
  );
  const pct = Math.round((doneCount / TOTAL) * 100);

  return (
    <AppLayout>
      <div className="space-y-6 max-w-3xl" data-testid="life-skills-page">
        <header>
          <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2 text-[#4A4A4A] flex items-center gap-2">
            <GraduationCap size={14} weight="fill" /> Life Skills
          </div>
          <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tight">Financial Foundations.</h1>
          <p className="text-[#4A4A4A] mt-3">Real-world money skills, in plain English. Work through each section at your own pace and tick it off.</p>
        </header>

        <div className="brutal-card p-5 bg-white" data-testid="life-skills-progress">
          <div className="flex items-center justify-between mb-2">
            <span className="font-display font-bold text-lg">Your progress</span>
            <span className="font-display font-black text-lg" data-testid="progress-count">{doneCount} / {TOTAL}</span>
          </div>
          <div className="h-4 w-full border-2 border-ink rounded-full overflow-hidden bg-paper">
            <div className="h-full bg-mint transition-all duration-500" style={{ width: `${pct}%` }} data-testid="progress-bar" />
          </div>
        </div>

        <div className="brutal-card p-4 bg-butter flex items-start gap-2 text-sm" data-testid="life-skills-disclaimer">
          <Warning size={20} weight="fill" className="mt-0.5 shrink-0" />
          <span>Educational guide, not personal financial advice. Figures are for the <strong>2026/27 UK tax year (6 April 2026 to 5 April 2027)</strong>, England, Wales and Northern Ireland unless stated. Rules change often, so <strong>verify on gov.uk</strong> before acting.</span>
        </div>

        {loading ? (
          <div className="brutal-card p-8 text-center text-[#4A4A4A]">Loading…</div>
        ) : (
          <>
            {SECTIONS.map((s) => {
              const Icon = s.icon;
              const done = completed.includes(s.key);
              return (
                <section key={s.key} className={`brutal-card p-6 ${done ? "bg-mint/40" : "bg-white"}`} data-testid={`life-section-${s.key}`}>
                  <div className="flex items-center gap-2 mb-3">
                    <div className="border-2 border-ink bg-white rounded-md p-2 shadow-brutal"><Icon size={20} weight="duotone" /></div>
                    <h2 className="font-display font-extrabold text-2xl">{s.title}</h2>
                  </div>
                  <div className="text-sm leading-relaxed text-[#333]">{s.body}</div>
                  <button
                    onClick={() => toggleSection(s.key)}
                    data-testid={`life-complete-${s.key}`}
                    className={`mt-5 brutal-btn inline-flex items-center gap-2 text-sm ${done ? "bg-ink text-white" : "bg-white hover:bg-mint"}`}
                  >
                    {done ? <CheckCircle size={16} weight="fill" /> : <Circle size={16} weight="bold" />}
                    {done ? "Completed" : "Mark as complete"}
                  </button>
                </section>
              );
            })}

            <section className={`brutal-card p-6 ${checklistDone ? "bg-mint/40" : "bg-lavender"}`} data-testid="life-section-checklist">
              <div className="flex items-center gap-2 mb-3">
                <div className="border-2 border-ink bg-white rounded-md p-2 shadow-brutal"><ListChecks size={20} weight="duotone" /></div>
                <h2 className="font-display font-extrabold text-2xl">10. A simple starting checklist</h2>
              </div>
              <ul className="space-y-2">
                {CHECKLIST.map(([k, t]) => {
                  const checked = checklist.includes(k);
                  return (
                    <li key={k}>
                      <button
                        onClick={() => toggleChecklistItem(k)}
                        data-testid={`checklist-${k}`}
                        className="w-full text-left flex items-start gap-3 p-3 rounded-md border-2 border-ink bg-white hover:bg-butter transition-colors"
                      >
                        {checked ? <CheckCircle size={20} weight="fill" className="mt-0.5 shrink-0" /> : <Circle size={20} weight="bold" className="mt-0.5 shrink-0 text-[#4A4A4A]" />}
                        <span className={`text-sm ${checked ? "line-through text-[#4A4A4A]" : ""}`}>{t}</span>
                      </button>
                    </li>
                  );
                })}
              </ul>
              <p className="text-sm text-[#4A4A4A] mt-4">
                For anything specific, such as which fund, whether to incorporate a business, or pension strategy, speak to a regulated adviser or accountant. Tax rules change often, so <strong>verify figures on gov.uk</strong> before acting.
              </p>
            </section>
          </>
        )}
      </div>
    </AppLayout>
  );
}
