// Curated subject + topic taxonomy. AI generates the actual content on demand.

// Grade levels grouped by region. Each entry has a "group" used for <optgroup>.
export const GRADE_LEVELS = [
  // Early years (universal)
  { value: "preschool", label: "Preschool (3–5)", group: "Early years", ages: "3-5" },
  { value: "elementary", label: "Elementary / Primary (6–10)", group: "Early years", ages: "6-10" },

  // Generic ISCED — works for any country
  { value: "lower_secondary", label: "Lower Secondary · ISCED 2 (11–15)", group: "Generic / ISCED", ages: "11-15" },
  { value: "upper_secondary", label: "Upper Secondary · ISCED 3 (15–18)", group: "Generic / ISCED", ages: "15-18" },

  // United Kingdom (KS3 → A-Levels)
  { value: "uk_y7", label: "UK · Year 7 (KS3, age 11–12)", group: "United Kingdom", ages: "11-12" },
  { value: "uk_y8", label: "UK · Year 8 (KS3, age 12–13)", group: "United Kingdom", ages: "12-13" },
  { value: "uk_y9", label: "UK · Year 9 (KS3, age 13–14)", group: "United Kingdom", ages: "13-14" },
  { value: "uk_y10", label: "UK · Year 10 (GCSE, age 14–15)", group: "United Kingdom", ages: "14-15" },
  { value: "uk_y11", label: "UK · Year 11 (GCSE, age 15–16)", group: "United Kingdom", ages: "15-16" },
  { value: "uk_y12", label: "UK · Year 12 (AS / Lower 6th, age 16–17)", group: "United Kingdom", ages: "16-17" },
  { value: "uk_y13", label: "UK · Year 13 (A2 / Upper 6th, age 17–18)", group: "United Kingdom", ages: "17-18" },

  // United States (High school)
  { value: "us_g9", label: "US · Grade 9 (Freshman, age 14–15)", group: "United States", ages: "14-15" },
  { value: "us_g10", label: "US · Grade 10 (Sophomore, age 15–16)", group: "United States", ages: "15-16" },
  { value: "us_g11", label: "US · Grade 11 (Junior, age 16–17)", group: "United States", ages: "16-17" },
  { value: "us_g12", label: "US · Grade 12 (Senior, age 17–18)", group: "United States", ages: "17-18" },

  // Canada
  { value: "ca_g9", label: "Canada · Grade 9 (age 14–15)", group: "Canada", ages: "14-15" },
  { value: "ca_g10", label: "Canada · Grade 10 (age 15–16)", group: "Canada", ages: "15-16" },
  { value: "ca_g11", label: "Canada · Grade 11 (age 16–17)", group: "Canada", ages: "16-17" },
  { value: "ca_g12", label: "Canada · Grade 12 (age 17–18)", group: "Canada", ages: "17-18" },

  // Australia
  { value: "au_y7", label: "Australia · Year 7 (age 12–13)", group: "Australia", ages: "12-13" },
  { value: "au_y8", label: "Australia · Year 8 (age 13–14)", group: "Australia", ages: "13-14" },
  { value: "au_y9", label: "Australia · Year 9 (age 14–15)", group: "Australia", ages: "14-15" },
  { value: "au_y10", label: "Australia · Year 10 (age 15–16)", group: "Australia", ages: "15-16" },
  { value: "au_y11", label: "Australia · Year 11 (age 16–17)", group: "Australia", ages: "16-17" },
  { value: "au_y12", label: "Australia · Year 12 (age 17–18)", group: "Australia", ages: "17-18" },

  // Germany
  { value: "de_sek1", label: "Germany · Sekundarstufe I (Klasse 5–10, 10–15)", group: "Germany", ages: "10-15" },
  { value: "de_sek2", label: "Germany · Sekundarstufe II (Klasse 11–13, 15–19)", group: "Germany", ages: "15-19" },

  // Japan
  { value: "jp_jhs", label: "Japan · Junior High 中学校 (age 12–15)", group: "Japan", ages: "12-15" },
  { value: "jp_shs", label: "Japan · Senior High 高校 (age 15–18)", group: "Japan", ages: "15-18" },

  // China
  { value: "cn_jhs", label: "China · Junior High 初中 (age 12–15)", group: "China", ages: "12-15" },
  { value: "cn_shs", label: "China · Senior High 高中 (age 15–18)", group: "China", ages: "15-18" },

  // Legacy / catch-all (kept for backwards compatibility with existing users)
  { value: "middle_school", label: "Middle School (11–13)", group: "Other", ages: "11-13" },
  { value: "high_school", label: "High School (14–18)", group: "Other", ages: "14-18" },

  // Higher education
  { value: "undergrad", label: "Undergraduate", group: "Higher education", ages: "18+" },
  { value: "grad", label: "Graduate / Master's", group: "Higher education", ages: "21+" },
  { value: "phd", label: "PhD / Doctoral", group: "Higher education", ages: "24+" },
];

export function gradeLevelLabel(value) {
  return GRADE_LEVELS.find((g) => g.value === value)?.label || value;
}

export function gradeLevelsGrouped() {
  const groups = {};
  for (const g of GRADE_LEVELS) {
    if (!groups[g.group]) groups[g.group] = [];
    groups[g.group].push(g);
  }
  return groups;
}

export const EXAM_BOARDS = [
  { value: "generic", label: "Generic (mock)" },
  { value: "aqa", label: "AQA (UK)" },
  { value: "edexcel", label: "Edexcel (UK)" },
  { value: "ocr", label: "OCR (UK)" },
  { value: "ib", label: "International Baccalaureate" },
  { value: "cie", label: "Cambridge International (CIE)" },
];

export const SUBJECT_CATEGORIES = [
  { id: "core", name: "Core Academic" },
  { id: "languages", name: "Foreign Languages" },
  { id: "arts", name: "Arts & Music" },
  { id: "physical", name: "Physical Education" },
  { id: "tech", name: "Technology & Vocational" },
  { id: "humanities", name: "Humanities & Social" },
];

export const SUBJECTS = [
  // CORE ACADEMIC
  {
    id: "mathematics", category: "core", name: "Mathematics", accent: "mint", accentHex: "#E6F7EB",
    tagline: "Arithmetic through calculus.", icon: "Function",
    topics: [
      { id: "arithmetic", name: "Arithmetic", sub: ["Place value", "Fractions", "Decimals", "Percentages", "Order of operations"] },
      { id: "algebra", name: "Algebra", sub: ["Linear equations", "Quadratics", "Inequalities", "Functions", "Logarithms"] },
      { id: "geometry", name: "Geometry", sub: ["Angles & lines", "Triangles", "Circles", "Coordinate geometry", "3D solids", "Proofs"] },
      { id: "trigonometry", name: "Trigonometry", sub: ["Sine/cosine/tangent", "Identities", "Unit circle", "Law of sines/cosines", "Inverse functions"] },
      { id: "calculus", name: "Calculus", sub: ["Limits", "Derivatives", "Integrals", "Applications", "Series"] },
      { id: "statistics", name: "Statistics", sub: ["Mean/median/mode", "Probability", "Distributions", "Hypothesis testing", "Regression"] },
    ],
  },
  {
    id: "english", category: "core", name: "English / Language Arts", accent: "lavender", accentHex: "#EBE6F7",
    tagline: "Read, write, analyse, speak.", icon: "BookOpen",
    topics: [
      { id: "grammar", name: "Grammar & Spelling", sub: ["Parts of speech", "Sentence structure", "Tenses", "Common errors"] },
      { id: "vocabulary", name: "Vocabulary", sub: ["Roots & affixes", "Synonyms/antonyms", "Idioms", "Context clues"] },
      { id: "reading", name: "Reading", sub: ["Comprehension", "Inference", "Main idea", "Author's purpose", "Text structure"] },
      { id: "writing", name: "Writing & Composition", sub: ["Narrative", "Persuasive essays", "Punctuation", "Citations", "Editing"] },
      { id: "literature", name: "Literature", sub: ["Poetry", "Short stories", "Shakespeare", "Modern novels", "Literary devices"] },
      { id: "speaking", name: "Public Speaking & Debate", sub: ["Argumentation", "Rebuttal", "Delivery", "Listening"] },
    ],
  },
  {
    id: "biology", category: "core", name: "Biology", accent: "mint", accentHex: "#E6F7EB",
    tagline: "Cells, genes, ecosystems.", icon: "Atom",
    topics: [
      { id: "cells", name: "Cells & Tissues", sub: ["Cell theory", "Organelles", "Cell division", "Tissues"] },
      { id: "genetics", name: "Genetics", sub: ["DNA & RNA", "Mendelian inheritance", "Mutations", "Biotechnology"] },
      { id: "evolution", name: "Evolution", sub: ["Natural selection", "Speciation", "Evidence", "Phylogenetics"] },
      { id: "ecology", name: "Ecology", sub: ["Ecosystems", "Food webs", "Biomes", "Conservation"] },
      { id: "human_body", name: "Human Body", sub: ["Circulatory", "Nervous", "Digestive", "Immune", "Endocrine"] },
    ],
  },
  {
    id: "chemistry", category: "core", name: "Chemistry", accent: "mint", accentHex: "#E6F7EB",
    tagline: "Matter, reactions, energy.", icon: "Atom",
    topics: [
      { id: "atoms", name: "Atoms & Elements", sub: ["Atomic structure", "Isotopes", "Electron configuration"] },
      { id: "periodic_table", name: "Periodic Table", sub: ["Trends", "Groups & periods", "Metals/nonmetals"] },
      { id: "bonds", name: "Chemical Bonds", sub: ["Ionic", "Covalent", "Metallic", "Intermolecular"] },
      { id: "reactions", name: "Reactions", sub: ["Stoichiometry", "Types of reactions", "Equilibrium", "Kinetics"] },
      { id: "acids_bases", name: "Acids & Bases", sub: ["pH", "Titration", "Buffers"] },
    ],
  },
  {
    id: "physics", category: "core", name: "Physics", accent: "mint", accentHex: "#E6F7EB",
    tagline: "Forces, fields, particles.", icon: "Atom",
    topics: [
      { id: "motion", name: "Motion", sub: ["Kinematics", "Vectors", "Projectile motion"] },
      { id: "forces", name: "Forces", sub: ["Newton's laws", "Friction", "Gravity"] },
      { id: "energy", name: "Energy", sub: ["Kinetic & potential", "Conservation", "Work & power"] },
      { id: "electricity", name: "Electricity & Magnetism", sub: ["Current", "Circuits", "Fields"] },
      { id: "waves", name: "Waves & Light", sub: ["Properties", "Sound", "Optics", "EM spectrum"] },
    ],
  },
  {
    id: "earth_science", category: "core", name: "Earth & Environmental Science", accent: "mint", accentHex: "#E6F7EB",
    tagline: "Geology, weather, climate.", icon: "Atom",
    topics: [
      { id: "geology", name: "Geology", sub: ["Rocks & minerals", "Plate tectonics", "Earthquakes", "Volcanoes"] },
      { id: "weather", name: "Weather & Climate", sub: ["Atmosphere", "Storms", "Climate change", "Water cycle"] },
      { id: "ecosystems", name: "Ecosystems", sub: ["Biomes", "Energy flow", "Human impact"] },
      { id: "oceans", name: "Oceans", sub: ["Currents", "Tides", "Marine life"] },
      { id: "space", name: "Space & Astronomy", sub: ["Solar system", "Stars", "Galaxies", "Cosmology"] },
    ],
  },
  {
    id: "history", category: "core", name: "History & Social Studies", accent: "lavender", accentHex: "#EBE6F7",
    tagline: "Sources, systems, time.", icon: "Bank",
    topics: [
      { id: "world_history", name: "World History", sub: ["Ancient", "Medieval", "Renaissance", "Industrial", "Modern"] },
      { id: "national_history", name: "National History", sub: ["Founding events", "Major wars", "Civil rights", "Modern era"] },
      { id: "civics", name: "Civics", sub: ["Rights & duties", "Citizenship", "Voting", "Civic engagement"] },
      { id: "government", name: "Government", sub: ["Branches of government", "Constitution", "Laws", "Political ideologies"] },
      { id: "primary_sources", name: "Primary Sources & Mock Trials", sub: ["Source analysis", "Bias", "Mock trial process", "Debate prep"] },
    ],
  },

  // FOREIGN LANGUAGES
  ...["Spanish", "French", "German", "Mandarin", "Latin"].map((lang) => ({
    id: `lang_${lang.toLowerCase()}`, category: "languages", name: lang, accent: "lavender", accentHex: "#EBE6F7",
    tagline: `Learn ${lang}: speak, read, write.`, icon: "Translate",
    topics: [
      { id: "vocabulary", name: "Vocabulary", sub: ["Greetings", "Numbers", "Food", "Travel", "Daily life"] },
      { id: "grammar", name: "Grammar", sub: ["Verbs & conjugation", "Tenses", "Sentence structure", "Cases"].filter(Boolean) },
      { id: "pronunciation", name: "Pronunciation", sub: ["Sounds", "Accents", "Tones", "Common mistakes"] },
      { id: "reading", name: "Reading", sub: ["Short texts", "News articles", "Stories"] },
      { id: "culture", name: "Culture", sub: ["Traditions", "History", "Cuisine", "Etiquette"] },
    ],
  })),

  // ARTS & MUSIC
  {
    id: "visual_arts", category: "arts", name: "Visual Arts", accent: "peach", accentHex: "#FFD8D1",
    tagline: "Draw, paint, sculpt, study.", icon: "PaintBrush",
    topics: [
      { id: "drawing", name: "Drawing", sub: ["Line", "Shading", "Perspective", "Anatomy"] },
      { id: "painting", name: "Painting", sub: ["Watercolor", "Acrylic", "Oil", "Colour theory"] },
      { id: "sculpture", name: "Sculpture", sub: ["Carving", "Modelling", "Casting", "Assembly"] },
      { id: "art_history", name: "Art History", sub: ["Renaissance", "Baroque", "Modernism", "Contemporary"] },
    ],
  },
  {
    id: "music", category: "arts", name: "Music", accent: "lavender", accentHex: "#EBE6F7",
    tagline: "Theory, practice, history.", icon: "MusicNotes",
    topics: [
      { id: "theory", name: "Music Theory", sub: ["Notation", "Scales", "Chords", "Harmony", "Rhythm"] },
      { id: "instrumental", name: "Instrumental", sub: ["Band", "Orchestra", "Solo practice"] },
      { id: "vocal", name: "Vocal & Choir", sub: ["Breathing", "Pitch", "Harmonies", "Performance"] },
      { id: "history", name: "Music History", sub: ["Baroque", "Classical", "Romantic", "Modern", "Jazz", "Pop"] },
    ],
  },
  {
    id: "drama", category: "arts", name: "Drama & Theater", accent: "peach", accentHex: "#FFD8D1",
    tagline: "Act, stage, analyse.", icon: "MaskHappy",
    topics: [
      { id: "acting", name: "Acting", sub: ["Voice", "Movement", "Character work", "Improvisation"] },
      { id: "stagecraft", name: "Stagecraft", sub: ["Lighting", "Sound", "Sets", "Costumes"] },
      { id: "script", name: "Script Analysis", sub: ["Structure", "Themes", "Subtext"] },
      { id: "performance", name: "Performance", sub: ["Rehearsal", "Stage presence", "Ensemble"] },
    ],
  },

  // PHYSICAL EDUCATION
  {
    id: "pe", category: "physical", name: "Physical Education & Health", accent: "peach", accentHex: "#FFD8D1",
    tagline: "Move, train, recover.", icon: "Barbell",
    topics: [
      { id: "fitness", name: "Fitness Basics", sub: ["Warm-up", "Cool-down", "Cardio", "Strength", "Flexibility"] },
      { id: "team_sports", name: "Team Sports", sub: ["Football", "Basketball", "Volleyball", "Rules & officiating"] },
      { id: "individual_sports", name: "Individual Sports", sub: ["Running", "Swimming", "Cycling", "Tennis"] },
      { id: "nutrition", name: "Nutrition", sub: ["Macronutrients", "Hydration", "Pre-workout meals", "Recovery food"] },
      { id: "health", name: "Health & Hygiene", sub: ["Sleep", "Mental health", "Hygiene", "First aid"] },
    ],
  },

  // TECHNOLOGY & VOCATIONAL
  {
    id: "computer_science", category: "tech", name: "Computer Science / IT", accent: "mint", accentHex: "#E6F7EB",
    tagline: "Code, design, automate.", icon: "Code",
    topics: [
      { id: "programming", name: "Programming Basics", sub: ["Variables", "Loops", "Functions", "Data structures"] },
      { id: "web", name: "Web Development", sub: ["HTML/CSS", "JavaScript", "APIs", "Databases"] },
      { id: "digital_literacy", name: "Digital Literacy", sub: ["Online safety", "Search skills", "Spreadsheets", "Word processing"] },
      { id: "cad", name: "CAD & Design", sub: ["2D drawing", "3D modelling", "Technical drawing"] },
      { id: "robotics", name: "Robotics", sub: ["Sensors", "Actuators", "Microcontrollers", "Logic"] },
    ],
  },
  {
    id: "home_ec", category: "tech", name: "Home Economics", accent: "butter", accentHex: "#FFF9E6",
    tagline: "Cook, sew, budget, manage.", icon: "ForkKnife",
    topics: [
      { id: "cooking", name: "Cooking", sub: ["Knife skills", "Recipes", "Food safety", "Meal planning"] },
      { id: "sewing", name: "Sewing & Textiles", sub: ["Hand stitches", "Machine basics", "Patterns", "Repairs"] },
      { id: "budgeting", name: "Budgeting", sub: ["Income & expenses", "Saving", "Credit", "Taxes"] },
      { id: "household", name: "Household Management", sub: ["Cleaning", "Time management", "Maintenance"] },
    ],
  },
  {
    id: "shop", category: "tech", name: "Shop / Trades", accent: "butter", accentHex: "#FFF9E6",
    tagline: "Make, fix, build.", icon: "Wrench",
    topics: [
      { id: "woodworking", name: "Woodworking", sub: ["Tools", "Joinery", "Finishing", "Safety"] },
      { id: "metalworking", name: "Metalworking", sub: ["Welding", "Forging", "Sheet metal", "Safety"] },
      { id: "auto", name: "Auto Mechanics", sub: ["Engines", "Maintenance", "Diagnostics", "Safety"] },
      { id: "tech_drawing", name: "Technical Drawing", sub: ["Orthographic", "Isometric", "Dimensioning"] },
    ],
  },

  // HUMANITIES & SOCIAL
  {
    id: "psychology", category: "humanities", name: "Psychology", accent: "lavender", accentHex: "#EBE6F7",
    tagline: "Mind, behaviour, development.", icon: "Brain",
    topics: [
      { id: "intro", name: "Introduction", sub: ["History", "Approaches", "Methods"] },
      { id: "cognition", name: "Cognition", sub: ["Memory", "Perception", "Decision-making"] },
      { id: "development", name: "Development", sub: ["Child", "Adolescent", "Adult"] },
      { id: "abnormal", name: "Abnormal Psychology", sub: ["Disorders", "Therapies", "Ethics"] },
      { id: "social_psych", name: "Social Psychology", sub: ["Conformity", "Persuasion", "Groups"] },
    ],
  },
  {
    id: "sociology", category: "humanities", name: "Sociology", accent: "lavender", accentHex: "#EBE6F7",
    tagline: "Society, systems, change.", icon: "UsersThree",
    topics: [
      { id: "intro", name: "Introduction", sub: ["Theories", "Methods", "Key thinkers"] },
      { id: "institutions", name: "Social Institutions", sub: ["Family", "Education", "Religion", "Economy"] },
      { id: "inequality", name: "Inequality", sub: ["Class", "Gender", "Race", "Globalisation"] },
      { id: "change", name: "Social Change", sub: ["Movements", "Revolutions", "Technology"] },
    ],
  },
  {
    id: "philosophy", category: "humanities", name: "Philosophy", accent: "lavender", accentHex: "#EBE6F7",
    tagline: "Logic, ethics, thought.", icon: "Lightbulb",
    topics: [
      { id: "logic", name: "Logic", sub: ["Arguments", "Fallacies", "Formal logic"] },
      { id: "ethics", name: "Ethics", sub: ["Virtue", "Deontology", "Consequentialism", "Applied"] },
      { id: "epistemology", name: "Epistemology", sub: ["Knowledge", "Justification", "Scepticism"] },
      { id: "metaphysics", name: "Metaphysics", sub: ["Reality", "Mind", "Free will"] },
      { id: "critical_thinking", name: "Critical Thinking", sub: ["Analysis", "Evaluation", "Reasoning"] },
    ],
  },
  {
    id: "geography", category: "humanities", name: "Geography", accent: "mint", accentHex: "#E6F7EB",
    tagline: "Place, people, planet.", icon: "Globe",
    topics: [
      { id: "physical_geography", name: "Physical Geography", sub: ["Landforms", "Climate", "Rivers", "Coasts"] },
      { id: "human_geography", name: "Human Geography", sub: ["Population", "Urbanisation", "Migration", "Development"] },
      { id: "maps", name: "Maps & GIS", sub: ["Map reading", "Projections", "GIS basics"] },
      { id: "environments", name: "Environments", sub: ["Sustainability", "Resources", "Hazards"] },
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

export function subjectsByCategory() {
  const map = {};
  for (const s of SUBJECTS) {
    if (!map[s.category]) map[s.category] = [];
    map[s.category].push(s);
  }
  return map;
}
