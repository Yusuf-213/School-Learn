import { gradeLevelsGrouped } from "@/lib/subjects";

export default function GradeLevelSelect({ value, onChange, className = "", testId, ...rest }) {
  const groups = gradeLevelsGrouped();
  const order = [
    "Early years", "Generic / ISCED",
    "United Kingdom", "United States", "Canada", "Australia",
    "Germany", "Japan", "China",
    "Other", "Higher education",
  ];
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
