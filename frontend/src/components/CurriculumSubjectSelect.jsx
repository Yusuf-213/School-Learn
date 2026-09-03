import { useEffect, useState } from "react";
import { fetchCurriculum } from "@/lib/curriculum";

/**
 * DB-backed subject picker — replaces the hardcoded subjects.js dropdowns.
 * Reads the /api/curriculum collection. Groups by key_stage.
 */
export default function CurriculumSubjectSelect({ value, onChange, testId, className = "", ...rest }) {
  const [rows, setRows] = useState([]);
  useEffect(() => { fetchCurriculum().then(setRows).catch(() => setRows([])); }, []);

  const groups = {};
  for (const r of rows) {
    const key = `${r.stage} · ${r.key_stage}`;
    (groups[key] = groups[key] || []).push(r);
  }

  return (
    <select
      data-testid={testId}
      value={value || ""}
      onChange={(e) => onChange(e.target.value)}
      className={`brutal-input bg-white ${className}`}
      {...rest}
    >
      <option value="">Choose a subject…</option>
      {Object.keys(groups).map((g) => (
        <optgroup key={g} label={g}>
          {groups[g].map((r) => (
            <option key={r.curriculum_id} value={r.subject}>{r.subject}</option>
          ))}
        </optgroup>
      ))}
    </select>
  );
}
