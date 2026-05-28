// Curated subject + topic taxonomy. AI generates the actual content on demand.
export const GRADE_LEVELS = [
  { value: "preschool", label: "Preschool (3-5)" },
  { value: "elementary", label: "Elementary (6-10)" },
  { value: "middle_school", label: "Middle School (11-13)" },
  { value: "high_school", label: "High School (14-18)" },
  { value: "undergrad", label: "Undergraduate" },
  { value: "grad", label: "Graduate" },
  { value: "phd", label: "PhD" },
];

export const SUBJECTS = [
  {
    id: "mathematics",
    name: "Mathematics",
    accent: "mint",
    accentHex: "#E6F7EB",
    tagline: "Numbers, patterns, proofs.",
    icon: "Function",
    topics: [
      { id: "arithmetic", name: "Arithmetic", sub: ["Place value", "Fractions", "Decimals", "Percentages", "Order of operations"] },
      { id: "algebra", name: "Algebra", sub: ["Linear equations", "Quadratics", "Inequalities", "Functions", "Logarithms"] },
      { id: "geometry", name: "Geometry", sub: ["Angles & lines", "Triangles", "Circles", "Coordinate geometry", "3D solids"] },
      { id: "statistics", name: "Statistics", sub: ["Mean/median/mode", "Probability", "Distributions", "Hypothesis testing", "Regression"] },
    ],
  },
  {
    id: "english",
    name: "English / Language Arts",
    accent: "lavender",
    accentHex: "#EBE6F7",
    tagline: "Read, write, analyse.",
    icon: "BookOpen",
    topics: [
      { id: "reading", name: "Reading", sub: ["Comprehension", "Inference", "Main idea", "Author's purpose", "Text structure"] },
      { id: "writing", name: "Writing", sub: ["Narrative", "Persuasive essays", "Grammar", "Punctuation", "Citations"] },
      { id: "literature", name: "Literature", sub: ["Poetry", "Short stories", "Shakespeare", "Modern novels", "Literary devices"] },
    ],
  },
  {
    id: "science",
    name: "Science",
    accent: "mint",
    accentHex: "#E6F7EB",
    tagline: "Observe, hypothesise, test.",
    icon: "Atom",
    topics: [
      { id: "biology", name: "Biology", sub: ["Cells", "Genetics", "Evolution", "Ecology", "Human body"] },
      { id: "chemistry", name: "Chemistry", sub: ["Atoms", "Periodic table", "Chemical bonds", "Reactions", "Acids & bases"] },
      { id: "physics", name: "Physics", sub: ["Motion", "Forces", "Energy", "Electricity", "Waves & light"] },
      { id: "earth_science", name: "Earth Science", sub: ["Weather & climate", "Plate tectonics", "Rocks & minerals", "Oceans", "Space"] },
    ],
  },
  {
    id: "history",
    name: "History / Social Studies",
    accent: "lavender",
    accentHex: "#EBE6F7",
    tagline: "Society, systems, time.",
    icon: "Bank",
    topics: [
      { id: "civics", name: "Civics", sub: ["Rights & duties", "Citizenship", "Voting", "Civic engagement"] },
      { id: "government", name: "Government", sub: ["Branches of government", "Constitution", "Laws", "Political ideologies"] },
      { id: "geography", name: "Geography", sub: ["Continents", "Capitals & countries", "Climate zones", "Maps & GIS", "Population"] },
    ],
  },
  {
    id: "pe",
    name: "Physical Education",
    accent: "peach",
    accentHex: "#FFD8D1",
    tagline: "Move, train, recover.",
    icon: "Barbell",
    topics: [
      { id: "fitness", name: "Fitness Basics", sub: ["Warm-up", "Cool-down", "Cardio", "Strength", "Flexibility"] },
      { id: "nutrition", name: "Nutrition", sub: ["Macronutrients", "Hydration", "Pre-workout meals", "Recovery food"] },
      { id: "sports", name: "Sports & Skills", sub: ["Team sports rules", "Individual sports", "Sportsmanship", "Officiating"] },
      { id: "health", name: "Health & Wellness", sub: ["Sleep", "Mental health", "Stress management", "Injury prevention"] },
    ],
  },
];

export function findSubject(id) {
  return SUBJECTS.find((s) => s.id === id);
}

export function findTopic(subjectId, topicId) {
  const s = findSubject(subjectId);
  return s?.topics.find((t) => t.id === topicId);
}
