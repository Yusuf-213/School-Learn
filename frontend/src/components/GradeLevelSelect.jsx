import { gradeLevelsGrouped, GRADE_LEVELS } from "@/lib/subjects";

export default function GradeLevelSelect({ value, onChange, className = "", testId, ...rest }) {
  const groups = gradeLevelsGrouped();
  // Derive order from GRADE_LEVELS so it can never drift out of sync with the taxonomy.
  const order = [];
  for (const g of GRADE_LEVELS) {
    if (!order.includes(g.group)) order.push(g.group);
  }
  return (
    <select
      data-testid={testId}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={`brutal-input bg-white ${className}`}
      {...rest}
    >
      {order.map((g) => groups[g] && (
        <optgroup key={g} label={g}>
          {groups[g].map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </optgroup>
      ))}
    </select>
  );
}
