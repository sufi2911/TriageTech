from pathlib import Path

# Project paths
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
MODEL_DIR = ROOT_DIR / "models"
DATA_FILE = DATA_DIR / "data.csv"
# Single Python artifact: holds the trained tree, medians, feature meta, and metrics.
MODEL_FILE = MODEL_DIR / "triage_tree.joblib"

# The CSV came from Kaggle (KTAS dataset) and uses Latin text encoding.
CSV_ENCODING = "latin-1"


RAW_TARGET_COL = "KTAS_expert"

KTAS_TO_URGENCY = {
    1: "Critical",
    2: "Critical",
    3: "Medium",
    4: "Low",
    5: "Low",
}

# Fixed ordering so colours / sorting are always consistent.
URGENCY_ORDER = ["Critical", "Medium", "Low"]
URGENCY_COLORS = {"Critical": "#d62728", "Medium": "#ff7f0e", "Low": "#2ca02c"}

# A one-line, jargon-free meaning for each class (shown to nurses).
URGENCY_MEANING = {
    "Critical": "See immediately - could be life threatening",
    "Medium": "Urgent - should be seen soon",
    "Low": "Not urgent - safe to wait",
}

# Features used by the model
# Numeric vitals / measurements (stored as text in the raw file - we coerce).
NUMERIC_FEATURES = ["Age", "SBP", "DBP", "HR", "RR", "BT", "Saturation", "NRS_pain"]

# Categorical / coded inputs (kept as small whole numbers).
CATEGORICAL_FEATURES = ["Sex", "Arrival mode", "Injury", "Mental", "Pain"]

# Symptom flags we derive from the free-text "Chief_complain" column.
# Each becomes a 0/1 feature and a simple tick-box on the screen.
SYMPTOM_FLAGS = [
    "chest_pain",
    "breathing_difficulty",
    "abdominal_pain",
    "head_or_neuro",
    "fever",
    "injury_trauma",
    "bleeding",
]

# Keyword lists used to turn complaint text into the flags above.
SYMPTOM_KEYWORDS = {
    "chest_pain": ["chest", "angina"],
    "breathing_difficulty": ["dyspnea", "dyspnoea", "sob", "breath", "respiratory distress",
                             "short of breath", "wheez", "choking"],
    "abdominal_pain": ["abd", "abdom", "epigastr", "stomach", "flank", "ascites"],
    "head_or_neuro": ["headache", "dizz", "vertigo", "seizure", "syncope", "faint",
                      "loc", "loss of consciousness", "stroke", "weakness", "altered",
                      "confus", "numb", "slurred"],
    "fever": ["fever", "febrile", "chill"],
    "injury_trauma": ["injury", "trauma", "fracture", "fx", "fall", "laceration",
                      "burn", "wound", "accident", "cut", "stab", "contusion", "sprain"],
    "bleeding": ["bleed", "hemorr", "haemorr", "hematemesis", "melena", "epistaxis",
                 "hematochezia", "blood"],
}

# Features the nurse actually enters (raw vitals, coded answers, symptom flags).
BASE_FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES + SYMPTOM_FLAGS


ENGINEERED_FEATURES = [
    "shock_index",
    "pulse_pressure",
    "mean_arterial_pressure",
    "abnormal_vitals",
]

# The exact column order the model expects (built once, reused everywhere).
FEATURE_COLUMNS = BASE_FEATURE_COLUMNS + ENGINEERED_FEATURES

SEX_OPTIONS = {"Female": 1, "Male": 2}

ARRIVAL_OPTIONS = {
    "Walked in": 1,
    "Public ambulance (emergency call)": 2,
    "Private car": 3,
    "Private ambulance": 4,
    "Public transport": 5,
    "Wheelchair": 6,
    "Other": 7,
}

INJURY_OPTIONS = {"No - feeling ill": 1, "Yes - injury or accident": 2}

MENTAL_OPTIONS = {
    "Awake and alert": 1,
    "Responds when spoken to": 2,
    "Responds only to pain": 3,
    "Not responding": 4,
}

PAIN_OPTIONS = {"No": 0, "Yes": 1}

# Friendly tick-box labels for the symptom flags.
SYMPTOM_LABELS = {
    "chest_pain": "Chest pain or pressure",
    "breathing_difficulty": "Trouble breathing",
    "abdominal_pain": "Stomach / belly pain",
    "head_or_neuro": "Headache, dizziness, fainting or weakness",
    "fever": "Fever",
    "injury_trauma": "Injury, accident or wound",
    "bleeding": "Bleeding",
}

# Vital-sign reference ranges (adult). Used for the risk score and for the
#  gentle "this number looks unusual" hints on screen.
VITAL_NORMAL_RANGES = {
    "HR": (60, 100),        # heart rate, beats per minute
    "RR": (12, 20),         # breaths per minute
    "SBP": (90, 140),       # blood pressure, top number
    "DBP": (60, 90),        # blood pressure, bottom number
    "BT": (36.0, 37.5),     # body temperature, Celsius
    "Saturation": (95, 100),  # oxygen level, %
}

# Friendly names + units for every numeric input (used to build the form).
VITAL_DISPLAY = {
    "Age": ("Age", "years", 0, 120, 1),
    "HR": ("Heart rate", "beats per minute", 20, 220, 1),
    "RR": ("Breathing rate", "breaths per minute", 4, 60, 1),
    "SBP": ("Blood pressure - top number", "mmHg", 40, 300, 1),
    "DBP": ("Blood pressure - bottom number", "mmHg", 20, 200, 1),
    "BT": ("Body temperature", "°C", 30.0, 43.0, 0.1),
    "Saturation": ("Oxygen level", "%", 50, 100, 1),
    "NRS_pain": ("Pain level", "0 = none, 10 = worst", 0, 10, 1),
}


def derive_symptoms(text) -> dict:

    flags = {f: 0 for f in SYMPTOM_FLAGS}
    if text is None:
        return flags
    low = str(text).lower()
    for flag, keywords in SYMPTOM_KEYWORDS.items():
        if any(k in low for k in keywords):
            flags[flag] = 1
    return flags
