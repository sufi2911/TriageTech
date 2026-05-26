# TriageTech — AI-Based Emergency Triage and Resource Allocation System

A decision-support prototype for hospital emergency departments. It does two things:

1. **Classifies patient urgency** — a **Decision Tree** reads the patient's vital signs and
   symptoms and sorts them into **Critical / Medium / Low**.
2. **Allocates limited resources** — a **cost-based priority queue** (the Uniform-Cost-Search
   idea) gives out ICU beds, ventilators, ward beds, and doctors to the most urgent and
   sickest patients first, until resources run out.

The web interface uses **plain, everyday English** (no heavy medical jargon) so that nurses
and front-line staff can operate it. The system is a **help for trained staff, not a
replacement** for their judgement.

---

## What it can do (app pages)

- **Check a patient** — enter a patient's details in simple English and get an urgency
  result, confidence, a warning score, danger-sign alerts, and the resources they likely need.
- **Waiting list** — see all waiting patients ordered by who should be seen first, and which
  resource each one gets or is waiting for.
- **Quick demo** — load real example patients from the dataset to see the system work fast.
- **How accurate is it?** — model accuracy, confusion matrix, per-class scores, and the
  features the model relies on most.
- **About** — a plain-English explanation of how the system works.

---

## How to run

You need **Python 3.10+**. All required packages are listed in `requirements.txt`
(streamlit, scikit-learn, pandas, numpy, altair, joblib).

```bash
# 1) (optional) install dependencies
pip install -r requirements.txt

# 2) start the app
streamlit run app.py
```

The app opens in your browser. The model is already trained (saved in `models/`), so it
starts immediately.

To **retrain** the model from the dataset:

```bash
python -m src.model
```

---

## Project structure

```
AI PROJECT/
├── app.py                  # Streamlit web app (the user interface)
├── requirements.txt        # Python dependencies
├── data/
│   └── data.csv            # KTAS emergency-triage dataset (~1,267 visits)
├── models/                 # trained model bundle (auto-generated)
│   └── triage_tree.joblib  # tree + medians + feature meta + metrics (all-in-one)
└── src/
    ├── config.py           # feature names, label mapping, plain-English labels
    ├── data_prep.py        # cleaning, missing values, symptom + engineered features
    ├── model.py            # train / evaluate / save the Decision Tree; predict
    └── allocation.py       # risk score, red-flag safety net, priority-queue allocator
```

Everything is pure Python — there are no JSON or config sidecar files. The
classification report and confusion matrix are computed in `src/model.py` and
saved inside the joblib bundle (the "How accurate is it?" page reads them
straight from there).

---

## How it works (short version)

- **Stage 1 — Decision Tree.** Chosen because it handles mixed numeric/categorical medical
  data, needs no scaling, models non-linear interactions, and — most importantly — its
  decisions are easy to read and explain. Tuned with `max_depth=6`, `min_samples_leaf=5`,
  pruning (`ccp_alpha=0.005`) and balanced class weights. Extra clinical features
  (shock index, pulse pressure, mean arterial pressure, abnormal-vital count) are computed
  automatically from the same readings the nurse enters.
- **Safety net.** Objective danger signs in the vitals (e.g. very low oxygen) can **escalate**
  a patient the model under-rated — shown on screen with the reason, never hidden.
- **Stage 2 — Cost-based priority queue.** Each patient gets a cost from urgency + risk score.
  A min-heap always serves the lowest-cost (most urgent, sickest) patient next and assigns
  resources if they are free, otherwise the patient waits and the bottleneck is reported.

## Results (summary)

| Model | Cross-validation accuracy |
|-------|---------------------------|
| Decision Tree (this project) | **68.8%** (test set: 67.3%) |
| Logistic Regression | 68.0% |
| k-Nearest Neighbours | 65.2% |
| Gaussian Naive Bayes | 62.2% |
| Random Forest (more accurate but not interpretable) | 71.7% |

Three-class triage (Critical / Medium / Low) on the KTAS dataset.

---

## Dataset

Public **KTAS (Korean Triage and Acuity Scale)** dataset from Kaggle
(*emergency-service-triage-application*), ~1,267 emergency-department visits. The 5-level
expert label is mapped to three classes (1–2 → Critical, 3 → Medium, 4–5 → Low). Vitals
stored as text are converted to numbers, and missing values are filled with the column median.

## Important note

This is an **academic prototype** for a university course. It has **not been clinically
validated** and must **not** be used for real patient care. Always rely on trained medical
staff and hospital procedures.
