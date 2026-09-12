"""Learnify UK curriculum seed data + grading logic.

Single source of truth for:
  • Primary (Reception → Y6) — KS1/KS2, teacher-assessed + KS2 SATs scaled scores.
  • GCSE — by exam board (AQA, Edexcel, OCR, Eduqas), Combined vs Triple science,
    Foundation vs Higher tier. Numeric 9-1 grades; grade boundaries entered retrospectively.
  • A-Level — full subject list incl. SQE Law route, Engineering disciplines, Quantum Physics.
  • IB Diploma — 6 subject groups + TOK/EE/CAS Core, HL/SL rules, 1-7 per subject (45 total).
  • Calculator use guard — restricted below the end of KS2.

The `seed_curriculum(db)` coroutine idempotently upserts one row per pathway into
Mongo's `curriculum` collection so schools can extend it without altering code.
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Year groups + grade-level normalisation helpers
# ---------------------------------------------------------------------------

PRIMARY_YEARS = ["uk_reception", "uk_y1", "uk_y2", "uk_y3", "uk_y4", "uk_y5", "uk_y6"]
KS1_YEARS = ["uk_y1", "uk_y2"]
KS2_YEARS = ["uk_y3", "uk_y4", "uk_y5", "uk_y6"]
SECONDARY_YEARS = ["uk_y7", "uk_y8", "uk_y9", "uk_y10", "uk_y11"]
GCSE_YEARS = ["uk_y10", "uk_y11"]
KS3_YEARS = ["uk_y7", "uk_y8", "uk_y9"]
SIXTH_FORM_YEARS = ["uk_y12", "uk_y13"]
IB_YEARS = ["ib_year_1", "ib_year_2"]

CALCULATOR_ALLOWED_YEARS = set(
    ["uk_y6"] + SECONDARY_YEARS + SIXTH_FORM_YEARS + IB_YEARS
    + ["uk_undergrad", "uk_masters", "uk_doctoral", "uk_pgce", "uk_apprentice"]
)


def can_use_calculator(grade_level: str | None) -> bool:
    """Return True only from the end of KS2 (Year 6) onwards.
    Below KS2, calculator-based practice/features must be disabled per DfE guidance."""
    if not grade_level:
        return False
    return grade_level in CALCULATOR_ALLOWED_YEARS


# ---------------------------------------------------------------------------
# Grading scales
# ---------------------------------------------------------------------------

GRADING_SCALES: dict[str, dict[str, Any]] = {
    # KS2 SATs — 80-120 scaled score. 100 = expected standard, 110 = greater depth.
    "ks2_scaled_score": {
        "type": "scaled_score",
        "range": [80, 120],
        "expected_standard": 100,
        "greater_depth": 110,
        "buckets": [
            {"min": 80, "max": 99, "label": "Working towards"},
            {"min": 100, "max": 109, "label": "Expected"},
            {"min": 110, "max": 120, "label": "Greater depth"},
        ],
        "notes": "Statutory: DfE scaled score 80-120, 100 is expected standard, 110 is greater depth.",
    },
    # Primary Science + Foundation subjects = Teacher-assessed only.
    "teacher_assessed": {
        "type": "teacher_assessed",
        "buckets": [
            {"label": "Working towards the expected standard"},
            {"label": "Working at the expected standard"},
            {"label": "Working at greater depth within the expected standard"},
        ],
        "notes": "No external examination; class teacher records against DfE descriptors.",
    },
    # GCSE 9-1.
    "gcse_9_1": {
        "type": "numeric_9_1",
        "grades": ["9", "8", "7", "6", "5", "4", "3", "2", "1", "U"],
        "tiers": ["foundation", "higher"],
        "tier_grade_range": {
            "foundation": ["5", "4", "3", "2", "1", "U"],
            "higher": ["9", "8", "7", "6", "5", "4", "U"],
        },
        "strong_pass": "5",
        "standard_pass": "4",
        "boundary_policy": "retrospective_per_board_per_series",
        "notes": (
            "Grade boundaries MUST be entered retrospectively for each board/subject/series. "
            "Do not hardcode boundaries — schools upload after each award."
        ),
    },
    # A-Level A*-E.
    "alevel_star_e": {
        "type": "letter_star_a_e",
        "grades": ["A*", "A", "B", "C", "D", "E", "U"],
        "ucas_points": {"A*": 56, "A": 48, "B": 40, "C": 32, "D": 24, "E": 16, "U": 0},
        "notes": "Ofqual A-Level 2010 onwards.",
    },
    # IB Diploma per-subject 1-7 with core bonus up to 3, total 45.
    "ib_1_7": {
        "type": "ib_1_7",
        "grades": [1, 2, 3, 4, 5, 6, 7],
        "subject_count": 6,
        "hl_min": 3, "hl_max": 4, "sl_min": 2, "sl_max": 3,
        "core_bonus_max": 3,           # TOK + EE matrix
        "max_total": 45,
        "pass_threshold": 24,
        "notes": "Six subjects, 3 or 4 at HL, 2 or 3 at SL. TOK + EE contribute up to 3 bonus points. CAS is a completion requirement.",
    },
}


# ---------------------------------------------------------------------------
# Primary (Reception → Year 6)
# ---------------------------------------------------------------------------

PRIMARY = {
    "pathway_id": "uk_primary",
    "name": "Primary (Reception – Year 6)",
    "key_stages": [
        {"id": "eyfs", "name": "EYFS", "years": ["uk_reception"]},
        {"id": "ks1", "name": "Key Stage 1", "years": KS1_YEARS},
        {"id": "ks2", "name": "Key Stage 2", "years": KS2_YEARS},
    ],
    "core_subjects": [
        {"id": "english", "name": "English", "grading": "ks2_scaled_score"},
        {"id": "maths", "name": "Mathematics", "grading": "ks2_scaled_score"},
        {"id": "science", "name": "Science", "grading": "teacher_assessed"},
    ],
    "foundation_subjects": [
        {"id": "art_design", "name": "Art & Design", "grading": "teacher_assessed"},
        {"id": "computing", "name": "Computing", "grading": "teacher_assessed"},
        {"id": "dt", "name": "Design & Technology", "grading": "teacher_assessed"},
        {"id": "geography", "name": "Geography", "grading": "teacher_assessed"},
        {"id": "history", "name": "History", "grading": "teacher_assessed"},
        {"id": "languages", "name": "Modern Foreign Languages (KS2)", "grading": "teacher_assessed"},
        {"id": "music", "name": "Music", "grading": "teacher_assessed"},
        {"id": "pe", "name": "Physical Education", "grading": "teacher_assessed"},
        {"id": "re", "name": "Religious Education", "grading": "teacher_assessed",
         "school_editable_syllabus": True,
         "parental_withdrawal": True,
         "notes": "Locally-agreed syllabus. Parents may withdraw a pupil from RE (Education Act 1996 s.71)."},
        {"id": "citizenship_pshe", "name": "PSHE & Citizenship", "grading": "teacher_assessed"},
    ],
    "statutory_reporting": [
        {
            "id": "swim_25m",
            "applies_to": ["uk_y6"],
            "required": True,
            "label": "Swimming — 25m by end of Year 6",
            "notes": (
                "Schools MUST report by the end of Year 6 whether each pupil can swim competently, "
                "confidently and proficiently over a distance of at least 25 metres, using a range "
                "of strokes effectively, and perform safe self-rescue in different water-based situations."
            ),
            "fields": [
                {"id": "swim_25m_confident", "label": "Swims 25m competently and confidently", "type": "bool"},
                {"id": "swim_strokes", "label": "Uses a range of strokes", "type": "bool"},
                {"id": "swim_self_rescue", "label": "Performs safe self-rescue", "type": "bool"},
            ],
        },
    ],
    "calculator_use": {
        "allowed_from_year": "uk_y6",
        "notes": "Calculator-based features (paper 2/3 practice, calculator quizzes) are DISABLED for Reception–Year 5.",
    },
}


# ---------------------------------------------------------------------------
# GCSE (Year 10-11) by exam board
# ---------------------------------------------------------------------------

_GCSE_COMMON_TIERS = ["foundation", "higher"]

_AQA_SUBJECTS = [
    "Mathematics", "English Language", "English Literature",
    "Biology", "Chemistry", "Physics", "Combined Science: Trilogy",
    "Geography", "History", "Religious Studies (Short & Full)",
    "French", "Spanish", "German",
    "Computer Science", "Business", "Economics",
    "Art & Design", "Design & Technology", "Music", "Drama",
    "Physical Education", "Sociology", "Psychology",
    "Statistics", "Media Studies", "Film Studies",
    "Food Preparation & Nutrition",
]
_EDEXCEL_SUBJECTS = [
    "Mathematics", "English Language", "English Literature",
    "Biology", "Chemistry", "Physics", "Combined Science",
    "Geography A/B", "History", "Religious Studies",
    "French", "Spanish", "German", "Mandarin Chinese",
    "Computer Science", "Business", "Economics",
    "Art & Design", "Design & Technology", "Music", "Drama",
    "Physical Education", "Psychology", "Statistics",
    "Media Studies", "Food Preparation & Nutrition",
    "Astronomy",
]
_OCR_SUBJECTS = [
    "Mathematics", "English Language", "English Literature",
    "Biology A/B (Twenty First Century Science)",
    "Chemistry A/B", "Physics A/B", "Combined Science A/B",
    "Geography A/B", "History A/B", "Religious Studies",
    "French", "Spanish", "German",
    "Computer Science", "Business", "Economics",
    "Art & Design", "Design & Technology", "Music", "Drama",
    "Physical Education", "Classical Civilisation", "Latin", "Ancient History",
    "Sociology", "Psychology",
    "Food Preparation & Nutrition",
]
_EDUQAS_SUBJECTS = [
    "Mathematics", "Mathematics — Numeracy", "English Language", "English Literature",
    "Biology", "Chemistry", "Physics", "Combined Science (Double Award)",
    "Geography", "History", "Religious Studies",
    "French", "Spanish", "German", "Welsh Second Language",
    "Computer Science", "Business", "Economics",
    "Art & Design", "Design & Technology", "Music", "Drama",
    "Physical Education", "Media Studies", "Film Studies",
    "Food & Nutrition", "Health & Social Care",
]


def _board(bid: str, name: str, subjects: list[str]) -> dict:
    return {
        "id": bid,
        "name": name,
        "subjects": [
            {
                "id": s.lower().replace(" ", "_").replace(":", "").replace("&", "and").replace("(", "").replace(")", "").replace(",", "").replace("/", "_")[:60],
                "name": s,
                "tiers": ["foundation", "higher"] if "Combined Science" in s or s in ("Mathematics", "Combined Science") else (
                    ["foundation", "higher"] if s in ("Mathematics — Numeracy", "Combined Science (Double Award)") else _tiers_for(s)
                ),
                "grading": "gcse_9_1",
                "science_route": _science_route(s),
            }
            for s in subjects
        ],
    }


def _tiers_for(subject_name: str) -> list[str]:
    # Common tiered GCSE subjects (Foundation/Higher entry).
    tiered = {
        "Mathematics", "Combined Science: Trilogy", "Combined Science", "Combined Science A/B",
        "Combined Science (Double Award)", "French", "Spanish", "German", "Mandarin Chinese",
        "Statistics", "Physical Education",
    }
    return _GCSE_COMMON_TIERS if subject_name in tiered else ["single_tier"]


def _science_route(subject_name: str) -> str | None:
    if subject_name in ("Biology", "Chemistry", "Physics"):
        return "triple"
    if "Combined Science" in subject_name:
        return "combined"
    return None


GCSE = {
    "pathway_id": "uk_gcse",
    "name": "GCSE (Year 10 – Year 11)",
    "years": GCSE_YEARS,
    "grading": "gcse_9_1",
    "science_routes": [
        {"id": "combined", "name": "Combined Science (Double Award)", "gcse_count": 2},
        {"id": "triple", "name": "Triple / Separate Sciences", "gcse_count": 3, "subjects": ["Biology", "Chemistry", "Physics"]},
    ],
    "tiers": _GCSE_COMMON_TIERS,
    "exam_boards": [
        _board("aqa", "AQA", _AQA_SUBJECTS),
        _board("edexcel", "Pearson Edexcel", _EDEXCEL_SUBJECTS),
        _board("ocr", "OCR", _OCR_SUBJECTS),
        _board("eduqas", "Eduqas / WJEC", _EDUQAS_SUBJECTS),
    ],
    "student_enrolment_metadata": [
        {"id": "tier", "type": "enum", "values": _GCSE_COMMON_TIERS, "notes": "Foundation or Higher — per subject, may differ."},
        {"id": "science_route", "type": "enum", "values": ["combined", "triple"], "notes": "Combined vs Triple science pathway."},
        {"id": "exam_board", "type": "enum", "values": ["aqa", "edexcel", "ocr", "eduqas"]},
    ],
    "notes": (
        "Numeric 9-1 scale. Grade boundaries are set by each awarding organisation after each series "
        "and MUST be entered retrospectively (see GRADING_SCALES.gcse_9_1.boundary_policy)."
    ),
}


# ---------------------------------------------------------------------------
# A-Level (Year 12-13) — includes SQE Law route, Engineering disciplines, Quantum Physics
# ---------------------------------------------------------------------------

A_LEVEL_SUBJECTS = [
    # Sciences
    {"id": "biology", "name": "Biology"},
    {"id": "chemistry", "name": "Chemistry"},
    {"id": "physics", "name": "Physics", "topics": [
        "Mechanics", "Waves", "Electricity", "Materials", "Nuclear physics",
        "Thermal physics", "Astrophysics", "Quantum Physics",
    ]},
    {"id": "further_maths", "name": "Further Mathematics"},
    {"id": "maths", "name": "Mathematics"},
    {"id": "computer_science", "name": "Computer Science"},

    # Humanities & Social Sciences
    {"id": "english_lit", "name": "English Literature"},
    {"id": "english_lang", "name": "English Language"},
    {"id": "english_lang_lit", "name": "English Language & Literature"},
    {"id": "history", "name": "History"},
    {"id": "geography", "name": "Geography"},
    {"id": "philosophy", "name": "Philosophy"},
    {"id": "politics", "name": "Politics"},
    {"id": "psychology", "name": "Psychology"},
    {"id": "sociology", "name": "Sociology"},
    {"id": "economics", "name": "Economics"},
    {"id": "business", "name": "Business"},
    {"id": "religious_studies", "name": "Religious Studies"},
    {"id": "classical_civ", "name": "Classical Civilisation"},
    {"id": "latin", "name": "Latin"},
    {"id": "ancient_history", "name": "Ancient History"},

    # Languages
    {"id": "french", "name": "French"},
    {"id": "spanish", "name": "Spanish"},
    {"id": "german", "name": "German"},
    {"id": "mandarin", "name": "Mandarin Chinese"},
    {"id": "italian", "name": "Italian"},
    {"id": "arabic", "name": "Arabic"},

    # Law — SQE-aligned pathway
    {"id": "law_sqe", "name": "Law (SQE pathway)",
     "notes": (
         "Post-2021 the Solicitors Qualifying Examination (SQE) replaced the LPC. "
         "This A-Level route prepares learners with SQE1 (functioning legal knowledge) "
         "and SQE2 (practical skills) awareness alongside classic constitutional / tort / contract topics."
     ),
     "topics": [
         "English legal system", "Constitutional & administrative law",
         "Tort", "Contract", "Criminal law", "Human rights",
         "SQE1: Functioning legal knowledge overview",
         "SQE2: Practical legal skills awareness",
         "Legal research & writing",
     ]},

    # Engineering disciplines (BTEC + A-Level Design/Engineering)
    {"id": "engineering_mechanical", "name": "Engineering — Mechanical"},
    {"id": "engineering_electrical", "name": "Engineering — Electrical & Electronic"},
    {"id": "engineering_civil", "name": "Engineering — Civil & Structural"},
    {"id": "engineering_aerospace", "name": "Engineering — Aerospace"},
    {"id": "engineering_chemical", "name": "Engineering — Chemical & Process"},
    {"id": "engineering_software", "name": "Engineering — Software & Systems"},

    # Creative
    {"id": "art_design", "name": "Art & Design"},
    {"id": "design_tech", "name": "Design & Technology (Product Design)"},
    {"id": "music", "name": "Music"},
    {"id": "music_tech", "name": "Music Technology"},
    {"id": "drama", "name": "Drama & Theatre Studies"},
    {"id": "film_studies", "name": "Film Studies"},
    {"id": "media_studies", "name": "Media Studies"},
    {"id": "photography", "name": "Photography"},

    # Physical
    {"id": "pe", "name": "Physical Education"},
    {"id": "dance", "name": "Dance"},
]

A_LEVEL = {
    "pathway_id": "uk_alevel",
    "name": "A-Level & AS-Level (Year 12 – Year 13)",
    "years": SIXTH_FORM_YEARS,
    "grading": "alevel_star_e",
    "subjects": A_LEVEL_SUBJECTS,
    "notes": (
        "Post-2015 linear A-Levels. Includes contemporary routes: SQE-aligned Law, "
        "Engineering discipline strands, and modern Physics topics (Quantum Physics)."
    ),
}


# ---------------------------------------------------------------------------
# IB Diploma
# ---------------------------------------------------------------------------

IB = {
    "pathway_id": "ib_diploma",
    "name": "International Baccalaureate Diploma Programme",
    "years": IB_YEARS,
    "grading": "ib_1_7",
    "depth_rules": {
        "total_subjects": 6,
        "hl_min": 3, "hl_max": 4,
        "sl_min": 2, "sl_max": 3,
        "notes": "Take one subject from each of Groups 1-5; Group 6 OR a second subject from Groups 2-4.",
    },
    "core": [
        {"id": "tok", "name": "Theory of Knowledge (TOK)", "assessment": "essay + exhibition"},
        {"id": "ee", "name": "Extended Essay (EE)", "assessment": "4,000-word research essay"},
        {"id": "cas", "name": "Creativity, Activity, Service (CAS)", "assessment": "portfolio; pass/fail — completion required"},
    ],
    "core_bonus_matrix": {
        "notes": "TOK + EE combine to award up to 3 bonus points on the IB 45-point scale.",
        "max_bonus": 3,
    },
    "groups": [
        {"id": "group_1", "name": "Studies in Language and Literature",
         "subjects": ["Language A: Literature", "Language A: Language and Literature", "Literature and Performance (SL only)"]},
        {"id": "group_2", "name": "Language Acquisition",
         "subjects": ["Language B (French/Spanish/German/Mandarin/Arabic/etc.)", "Language ab initio (SL only)", "Classical Languages"]},
        {"id": "group_3", "name": "Individuals and Societies",
         "subjects": ["Business Management", "Economics", "Geography", "Global Politics", "History",
                      "Information Technology in a Global Society (ITGS)", "Philosophy", "Psychology",
                      "Social & Cultural Anthropology", "World Religions (SL)"]},
        {"id": "group_4", "name": "Sciences",
         "subjects": ["Biology", "Chemistry", "Physics", "Computer Science", "Design Technology",
                      "Environmental Systems & Societies", "Sports, Exercise & Health Science"]},
        {"id": "group_5", "name": "Mathematics",
         "subjects": ["Mathematics: Analysis & Approaches (SL/HL)", "Mathematics: Applications & Interpretation (SL/HL)"]},
        {"id": "group_6", "name": "The Arts (optional — may swap for a 2nd Group 2-4 subject)",
         "subjects": ["Visual Arts", "Music", "Theatre", "Dance", "Film"]},
    ],
    "notes": (
        "Awarded out of 45 points (6 subjects × 7 max + 3 core bonus). "
        "24 minimum to earn the Diploma with all CAS/TOK/EE completed."
    ),
}


# ---------------------------------------------------------------------------
# Aggregated tree + calculator guard export
# ---------------------------------------------------------------------------

CURRICULUM_TREE = {
    "version": "2026.03",
    "country": "GB",
    "pathways": [PRIMARY, GCSE, A_LEVEL, IB],
    "grading_scales": GRADING_SCALES,
    "calculator_guard": {
        "rule": "Restricted below end of KS2 (Year 6).",
        "allowed_years": sorted(list(CALCULATOR_ALLOWED_YEARS)),
        "denied_years": ["uk_reception", "uk_y1", "uk_y2", "uk_y3", "uk_y4", "uk_y5"],
    },
}


async def seed_curriculum(db) -> dict:
    """Upsert the curriculum tree as a single doc in `db.curriculum`.

    Idempotent — writes only when the checksum changes, so a restart is cheap.
    Schools may override individual subjects/topics via `/api/school/curriculum-overrides`
    without editing this file.
    """
    import hashlib, json
    from datetime import datetime, timezone

    payload = json.dumps(CURRICULUM_TREE, sort_keys=True, ensure_ascii=False)
    checksum = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    existing = await db.curriculum.find_one({"doc_id": "uk_curriculum_v1"})
    if existing and existing.get("checksum") == checksum:
        return {"status": "unchanged", "checksum": checksum}
    await db.curriculum.update_one(
        {"doc_id": "uk_curriculum_v1"},
        {"$set": {
            "doc_id": "uk_curriculum_v1",
            "tree": CURRICULUM_TREE,
            "checksum": checksum,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )
    return {"status": "seeded", "checksum": checksum}
