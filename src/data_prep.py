"""
Data loading and cleaning for TriageTech.

Raw file quirks this module handles:
  - text-encoded as latin-1 (came from Kaggle)
  - vitals stored as TEXT with comma decimals  (e.g. "3,95")  -> real numbers
  - oxygen level missing ~54% of the time        -> filled with the median
  - pain score blank when the patient has no pain -> filled with 0
  - target KTAS_expert is 1-5                      -> mapped to 3 urgency classes

The output is a tidy feature table (X) and the urgency labels (y) that the
Decision Tree can train on. The same cleaning helpers are reused at predict
time so a live patient is processed exactly like the training data.
"""

import numpy as np
import pandas as pd

from . import config as C


def add_engineered_features(X: pd.DataFrame) -> pd.DataFrame:
    #Add the computed clinical features to a frame that already has the base columns. Used in training and at predict time so the two always match.
    
    X = X.copy()
    sbp = X["SBP"].replace(0, np.nan)
    X["shock_index"] = (X["HR"] / sbp).clip(lower=0, upper=5).fillna(0.7)
    X["pulse_pressure"] = X["SBP"] - X["DBP"]
    X["mean_arterial_pressure"] = X["DBP"] + (X["SBP"] - X["DBP"]) / 3.0

    abn = ((X["HR"] > 100) | (X["HR"] < 60)).astype(int)
    abn += ((X["RR"] > 20) | (X["RR"] < 12)).astype(int)
    abn += ((X["SBP"] > 140) | (X["SBP"] < 100)).astype(int)
    abn += (X["Saturation"] < 94).astype(int)
    abn += ((X["BT"] >= 38) | (X["BT"] < 36)).astype(int)
    abn += (X["Mental"] > 1).astype(int)
    X["abnormal_vitals"] = abn
    return X


def load_raw_dataframe(path=None) -> pd.DataFrame:
    #Read the raw CSV exactly as it is (no cleaning yet).
    path = path or C.DATA_FILE
    # sep=None + python engine auto-detects the delimiter; the file is commas.
    return pd.read_csv(path, encoding=C.CSV_ENCODING, sep=None, engine="python")


def _to_number(series: pd.Series) -> pd.Series:
    #Coerce a text column (possibly with comma decimals) to numbers.
    cleaned = (
        series.astype(str)
        .str.replace(",", ".", regex=False)
        .str.strip()
        .replace({"": None, "nan": None, "NaN": None})
    )
    return pd.to_numeric(cleaned, errors="coerce")


def build_feature_frame(raw: pd.DataFrame):
    
    df = raw.copy()

    # 1) numeric vitals: text -> numbers
    for col in C.NUMERIC_FEATURES:
        df[col] = _to_number(df[col])

    # 2) no pain reported -> pain score of 0 (not "unknown")
    if "Pain" in df.columns:
        df.loc[df["Pain"] == 0, "NRS_pain"] = df.loc[df["Pain"] == 0, "NRS_pain"].fillna(0)

    # 3) symptom flags from the free-text complaint column
    complaint_col = "Chief_complain" if "Chief_complain" in df.columns else None
    flag_rows = [
        C.derive_symptoms(df.at[i, complaint_col] if complaint_col else None)
        for i in df.index
    ]
    flags_df = pd.DataFrame(flag_rows, index=df.index)
    for flag in C.SYMPTOM_FLAGS:
        df[flag] = flags_df[flag]

    # 4) map target 1-5 -> 3 classes, drop rows with no valid label
    df["urgency"] = df[C.RAW_TARGET_COL].map(C.KTAS_TO_URGENCY)
    df = df.dropna(subset=["urgency"])

    # 5) assemble the base features in the expected order
    X = df[C.BASE_FEATURE_COLUMNS].copy()

    # 6) fill any remaining gaps with the column median and remember the value
    medians = {}
    for col in C.NUMERIC_FEATURES + C.CATEGORICAL_FEATURES:
        med = float(X[col].median())
        medians[col] = med
        X[col] = X[col].fillna(med)
    # symptom flags never have gaps, but be safe
    for flag in C.SYMPTOM_FLAGS:
        X[flag] = X[flag].fillna(0).astype(int)

    # 7) add the computed clinical features (after gaps are filled)
    X = add_engineered_features(X)
    X = X[C.FEATURE_COLUMNS]

    y = df["urgency"]
    return X, y, medians


def patient_dict_to_features(patient: dict, medians: dict) -> pd.DataFrame:
    #Build a one-row feature frame for a single live patient.
    row = {}
    for col in C.NUMERIC_FEATURES + C.CATEGORICAL_FEATURES:
        val = patient.get(col, None)
        if val is None or (isinstance(val, float) and pd.isna(val)):
            val = medians.get(col, 0)
        row[col] = val
    for flag in C.SYMPTOM_FLAGS:
        row[flag] = int(patient.get(flag, 0))
    X = pd.DataFrame([row], columns=C.BASE_FEATURE_COLUMNS)
    X = add_engineered_features(X)
    return X[C.FEATURE_COLUMNS]
