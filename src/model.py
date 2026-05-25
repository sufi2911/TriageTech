"""
The Decision Tree (Stage 1 of the system: supervised classification).

This module trains a single, interpretable Decision Tree that reads a patient's
vitals + symptoms and predicts an urgency class (Critical / Medium / Low).

Why a Decision Tree (per the project design):
  - handles mixed numeric + categorical data
  - the decision path is easy to read and explain to a nurse
  - class_weight="balanced" stops the rarer Critical cases being ignored

Artifacts saved to /models so the app starts instantly:
  - triage_tree.joblib   the trained tree + the medians used for filling gaps
  - feature_meta.json    feature order, classes, medians (human readable)
  - metrics.json         accuracy + report + confusion matrix + importances
"""

import json

import joblib
import numpy as np
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.tree import DecisionTreeClassifier, export_text

from . import config as C
from . import data_prep


def train_and_save(random_state: int = 42) -> dict:
    """Train the tree on the full dataset, evaluate it, and save everything."""
    raw = data_prep.load_raw_dataframe()
    X, y, medians = data_prep.build_feature_frame(raw)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=random_state, stratify=y
    )

    # Depth/leaf/pruning chosen by a multi-seed cross-validation sweep over the
    # engineered feature set. ccp_alpha prunes weak branches so the tree stays
    # readable and generalises instead of memorising the ~1,200 training rows.
    clf = DecisionTreeClassifier(
        criterion="gini",
        max_depth=6,
        min_samples_leaf=5,
        ccp_alpha=0.005,
        class_weight="balanced",
        random_state=random_state,
    )
    clf.fit(X_train, y_train)

    # ---- evaluation -------------------------------------------------------
    y_pred = clf.predict(X_test)
    acc = float(accuracy_score(y_test, y_pred))
    # Shuffled folds: the raw file is ordered, so unshuffled CV is misleading.
    cv_splitter = StratifiedKFold(n_splits=5, shuffle=True, random_state=random_state)
    cv = cross_val_score(clf, X, y, cv=cv_splitter)
    report = classification_report(
        y_test, y_pred, labels=C.URGENCY_ORDER, output_dict=True, zero_division=0
    )
    cm = confusion_matrix(y_test, y_pred, labels=C.URGENCY_ORDER).tolist()
    importances = sorted(
        zip(C.FEATURE_COLUMNS, clf.feature_importances_.tolist()),
        key=lambda t: t[1],
        reverse=True,
    )

    metrics = {
        "accuracy": acc,
        "cv_mean": float(cv.mean()),
        "cv_std": float(cv.std()),
        "n_total": int(len(X)),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "classes": C.URGENCY_ORDER,
        "confusion_matrix": cm,
        "report": report,
        "feature_importances": importances,
        "class_counts": y.value_counts().to_dict(),
        "tree_text": export_text(clf, feature_names=list(C.FEATURE_COLUMNS)),
    }

    meta = {
        "feature_columns": C.FEATURE_COLUMNS,
        "classes": list(clf.classes_),
        "medians": medians,
    }

    # ---- save -------------------------------------------------------------
    C.MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": clf, "medians": medians,
                 "feature_columns": C.FEATURE_COLUMNS}, C.MODEL_FILE)
    C.META_FILE.write_text(json.dumps(meta, indent=2))
    C.METRICS_FILE.write_text(json.dumps(metrics, indent=2))
    return metrics


def load_bundle():
    """Load the saved model bundle (trains it first if missing)."""
    if not C.MODEL_FILE.exists():
        train_and_save()
    return joblib.load(C.MODEL_FILE)


def load_metrics() -> dict:
    if not C.METRICS_FILE.exists():
        return {}
    return json.loads(C.METRICS_FILE.read_text())


def predict_patient(bundle, patient: dict) -> dict:
    """Predict urgency for one live patient.

    Returns the predicted class, the probability of each class, and a short
    plain-English reason built from the most important features the tree used.
    """
    model = bundle["model"]
    medians = bundle["medians"]
    X = data_prep.patient_dict_to_features(patient, medians)

    pred = str(model.predict(X)[0])
    proba = {cls: float(p) for cls, p in zip(model.classes_, model.predict_proba(X)[0])}
    confidence = proba.get(pred, max(proba.values()))

    return {
        "urgency": pred,
        "confidence": confidence,
        "probabilities": proba,
        "meaning": C.URGENCY_MEANING.get(pred, ""),
    }


if __name__ == "__main__":
    # Allow:  python -m src.model   to (re)train from the command line.
    m = train_and_save()
    print(f"Trained. Test accuracy = {m['accuracy']:.3f} "
          f"| 5-fold CV = {m['cv_mean']:.3f} +/- {m['cv_std']:.3f}")
    print("Top features:")
    for name, imp in m["feature_importances"][:8]:
        print(f"  {name:22s} {imp:.3f}")
