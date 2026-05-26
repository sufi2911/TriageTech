"""
The Decision Tree (Stage 1 of the system: supervised classification).

This module trains a single, interpretable Decision Tree that reads a patient's
vitals + symptoms and predicts an urgency class (Critical / Medium / Low).

Why a Decision Tree (per the project design):
  - handles mixed numeric + categorical data
  - the decision path is easy to read and explain to a nurse
  - class_weight="balanced" stops the rarer Critical cases being ignored

Everything is saved inside one Python artifact (triage_tree.joblib) so the
project stays pure-Python: no JSON, no extra config files.

The bundle contains:
  - "model"            the trained tree
  - "medians"          column medians used to fill missing inputs
  - "feature_columns"  exact feature order the model expects
  - "classes"          class labels in the order the model returns them
  - "metrics"          accuracy, classification report, confusion matrix,
                       feature importances and a printable tree
"""

import joblib
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

    y_pred = clf.predict(X_test)
    acc = float(accuracy_score(y_test, y_pred))

    # Shuffled folds: the raw file is ordered, so unshuffled CV is misleading.
    cv_splitter = StratifiedKFold(n_splits=5, shuffle=True, random_state=random_state)
    cv = cross_val_score(clf, X, y, cv=cv_splitter)

    # Classification report and confusion matrix (kept in plain Python types).
    report = classification_report(
        y_test, y_pred, labels=C.URGENCY_ORDER, output_dict=True, zero_division=0
    )
    report_text = classification_report(
        y_test, y_pred, labels=C.URGENCY_ORDER, zero_division=0
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
        "report_text": report_text,
        "feature_importances": importances,
        "class_counts": y.value_counts().to_dict(),
        "tree_text": export_text(clf, feature_names=list(C.FEATURE_COLUMNS)),
    }

    bundle = {
        "model": clf,
        "medians": medians,
        "feature_columns": C.FEATURE_COLUMNS,
        "classes": list(clf.classes_),
        "metrics": metrics,
    }

    C.MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, C.MODEL_FILE)
    return metrics


def load_bundle():
    """Load the saved model bundle (trains it first if missing)."""
    if not C.MODEL_FILE.exists():
        train_and_save()
    return joblib.load(C.MODEL_FILE)


def load_metrics() -> dict:
    """Return the metrics dict stored inside the joblib bundle."""
    if not C.MODEL_FILE.exists():
        return {}
    bundle = joblib.load(C.MODEL_FILE)
    return bundle.get("metrics", {})


def predict_patient(bundle, patient: dict) -> dict:
    """Predict urgency for one live patient."""
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


def _print_confusion_matrix(cm, classes) -> None:
    """Pretty-print the confusion matrix to the terminal."""
    width = max(len(c) for c in classes) + 2
    header = " " * (width + 2) + "  ".join(f"Said {c:<{width}}" for c in classes)
    print(header)
    for row_label, row in zip(classes, cm):
        cells = "  ".join(f"{v:<{width + 4}}" for v in row)
        print(f"Actual {row_label:<{width}}{cells}")


if __name__ == "__main__":
    # python -m src.model   to retrain.
    m = train_and_save()
    print(f"Trained. Test accuracy = {m['accuracy']:.3f} "
          f"| 5-fold CV = {m['cv_mean']:.3f} +/- {m['cv_std']:.3f}")

    print("\nClassification report:")
    print(m["report_text"])

    print("Confusion matrix (rows = actual, columns = predicted):")
    _print_confusion_matrix(m["confusion_matrix"], m["classes"])

    print("\nTop features:")
    for name, imp in m["feature_importances"][:8]:
        print(f"  {name:22s} {imp:.3f}")
