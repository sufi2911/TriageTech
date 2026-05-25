"""
TriageTech - AI-Based Emergency Triage and Resource Allocation System
COMP360-B  |  Team: Laiba Nouman & Sufyan Abbasi

A nurse-friendly front end. Plain English everywhere - no heavy medical jargon.

Run it with:
    streamlit run app.py
"""

import random

import altair as alt
import pandas as pd
import streamlit as st

from src import allocation as alloc
from src import config as C
from src import data_prep, model

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(page_title="TriageTech", page_icon="🏥", layout="wide")


@st.cache_resource(show_spinner="Getting the system ready...")
def get_bundle():
    return model.load_bundle()


@st.cache_data
def get_metrics():
    return model.load_metrics()


@st.cache_data
def get_raw_data():
    return data_prep.load_raw_dataframe()


BUNDLE = get_bundle()

# ---------------------------------------------------------------------------
# Session state (remembers the waiting list and the resource settings)
# ---------------------------------------------------------------------------
if "queue" not in st.session_state:
    st.session_state.queue = []
if "resources" not in st.session_state:
    st.session_state.resources = dict(alloc.DEFAULT_RESOURCES)
if "last_assessment" not in st.session_state:
    st.session_state.last_assessment = None


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def urgency_badge(u: str, big: bool = False) -> str:
    color = C.URGENCY_COLORS.get(u, "#666")
    size = "1.4rem" if big else "0.95rem"
    pad = "8px 18px" if big else "3px 10px"
    return (f'<span style="background:{color};color:white;padding:{pad};'
            f'border-radius:14px;font-weight:700;font-size:{size};">{u}</span>')


def build_patient(name, age, sex_label, arrival_label, injury_label, mental_label,
                  pain_label, pain_score, symptom_labels, complaint_text,
                  hr, rr, sbp, dbp, bt, sat):
    """Turn the friendly form answers into a model-ready patient dict."""
    # selected symptom checkboxes -> flag keys
    label_to_flag = {v: k for k, v in C.SYMPTOM_LABELS.items()}
    flags = {f: 0 for f in C.SYMPTOM_FLAGS}
    for lbl in symptom_labels:
        flags[label_to_flag[lbl]] = 1
    # also read any typed complaint text
    for k, v in C.derive_symptoms(complaint_text).items():
        if v:
            flags[k] = 1

    patient = {
        "name": name.strip() or "Unnamed patient",
        "complaint": complaint_text.strip(),
        "Age": age,
        "Sex": C.SEX_OPTIONS[sex_label],
        "Arrival mode": C.ARRIVAL_OPTIONS[arrival_label],
        "Injury": C.INJURY_OPTIONS[injury_label],
        "Mental": C.MENTAL_OPTIONS[mental_label],
        "Pain": C.PAIN_OPTIONS[pain_label],
        "NRS_pain": pain_score if C.PAIN_OPTIONS[pain_label] == 1 else 0,
        "HR": hr, "RR": rr, "SBP": sbp, "DBP": dbp, "BT": bt, "Saturation": sat,
    }
    patient.update(flags)
    return patient


def assess(patient: dict) -> dict:
    """Run the model + safety checks for one patient and bundle the answer."""
    pred = model.predict_patient(BUNDLE, patient)
    risk = alloc.compute_risk_score(patient)
    flags, severe = alloc.red_flags(patient)
    eff = alloc.effective_urgency(pred["urgency"], severe)
    return {
        **patient,
        "urgency": pred["urgency"],
        "model_urgency": pred["urgency"],
        "effective_urgency": eff,
        "escalated": eff != pred["urgency"],
        "confidence": pred["confidence"],
        "probabilities": pred["probabilities"],
        "risk": risk,
        "red_flags": flags,
        "severe_flags": severe,
    }


# ---------------------------------------------------------------------------
# Sidebar: navigation + hospital resources
# ---------------------------------------------------------------------------
st.sidebar.title("🏥 TriageTech")
st.sidebar.caption("Emergency triage helper")

page = st.sidebar.radio(
    "Go to",
    ["Check a patient", "Waiting list", "Quick demo", "How accurate is it?", "About"],
)

st.sidebar.divider()
st.sidebar.subheader("Hospital resources right now")
st.sidebar.caption("Change these to match what your hospital has free.")
res = st.session_state.resources
res["icu_beds"] = st.sidebar.number_input("ICU beds free", 0, 100, res["icu_beds"])
res["ventilators"] = st.sidebar.number_input("Ventilators free", 0, 100, res["ventilators"])
res["ward_beds"] = st.sidebar.number_input("Ward beds free", 0, 200, res["ward_beds"])
res["doctors"] = st.sidebar.number_input("Doctors available", 0, 100, res["doctors"])

st.sidebar.divider()
st.sidebar.metric("Patients on the waiting list", len(st.session_state.queue))


# ===========================================================================
# PAGE 1 - Check a patient
# ===========================================================================
if page == "Check a patient":
    st.title("Check how urgent a patient is")
    st.write("Fill in what you know about the patient. You can leave a box empty "
             "if a reading was not taken.")

    with st.form("patient_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            name = st.text_input("Patient name or ID", placeholder="e.g. Bed 4 / Ali")
            age = st.number_input("Age (years)", 0, 120, 40)
            sex_label = st.radio("Sex", list(C.SEX_OPTIONS.keys()), horizontal=True)
            arrival_label = st.selectbox("How did the patient arrive?",
                                         list(C.ARRIVAL_OPTIONS.keys()))
            injury_label = st.radio("Is this an injury or accident?",
                                    list(C.INJURY_OPTIONS.keys()))
        with c2:
            mental_label = st.selectbox("How awake is the patient?",
                                        list(C.MENTAL_OPTIONS.keys()))
            pain_label = st.radio("Is the patient in pain?",
                                  list(C.PAIN_OPTIONS.keys()), horizontal=True)
            pain_score = st.slider("Pain level (0 = none, 10 = worst)", 0, 10, 0)
            symptom_labels = st.multiselect("Main problems (tick all that apply)",
                                            list(C.SYMPTOM_LABELS.values()))
            complaint_text = st.text_input("Anything else? (optional, in your words)",
                                           placeholder="e.g. coughing since morning")
        with c3:
            st.markdown("**Vital signs** (leave empty if not measured)")
            hr = st.number_input("Heart rate (beats per minute)", 20, 250, value=None)
            rr = st.number_input("Breathing rate (breaths per minute)", 4, 70, value=None)
            sbp = st.number_input("Blood pressure - top number", 40, 300, value=None)
            dbp = st.number_input("Blood pressure - bottom number", 20, 200, value=None)
            bt = st.number_input("Body temperature (°C)", 30.0, 43.0, value=None, step=0.1)
            sat = st.number_input("Oxygen level (%)", 50, 100, value=None)

        submitted = st.form_submit_button("Check urgency", type="primary",
                                          use_container_width=True)

    if submitted:
        patient = build_patient(name, age, sex_label, arrival_label, injury_label,
                                mental_label, pain_label, pain_score, symptom_labels,
                                complaint_text, hr, rr, sbp, dbp, bt, sat)
        st.session_state.last_assessment = assess(patient)

    # show the result (kept after the form reruns)
    a = st.session_state.last_assessment
    if a is not None:
        st.divider()
        final = a["effective_urgency"]
        st.markdown(f"### Result for **{a['name']}**")
        cc1, cc2 = st.columns([1, 1])
        with cc1:
            st.markdown("How urgent:", help="The colour shows how quickly the "
                        "patient should be seen.")
            st.markdown(urgency_badge(final, big=True), unsafe_allow_html=True)
            st.write(f"**{C.URGENCY_MEANING[final]}**")
            if a["escalated"]:
                st.warning(f"The computer model first said **{a['model_urgency']}**, "
                           f"but because of the danger signs below the patient has been "
                           f"moved up to **{final}**.")
            st.metric("How sure the model is", f"{a['confidence']*100:.0f}%")
            st.metric("Warning score from vital signs", f"{a['risk']} / 100")
        with cc2:
            st.markdown("**Chance of each level (model)**")
            prob_df = pd.DataFrame(
                {"Level": list(a["probabilities"].keys()),
                 "Chance": [round(v * 100) for v in a["probabilities"].values()]}
            )
            chart = (alt.Chart(prob_df).mark_bar().encode(
                x=alt.X("Chance:Q", title="Chance (%)", scale=alt.Scale(domain=[0, 100])),
                y=alt.Y("Level:N", sort=C.URGENCY_ORDER, title=""),
                color=alt.Color("Level:N",
                                scale=alt.Scale(domain=C.URGENCY_ORDER,
                                                range=[C.URGENCY_COLORS[u] for u in C.URGENCY_ORDER]),
                                legend=None),
            ).properties(height=160))
            st.altair_chart(chart, use_container_width=True)

        if a["red_flags"]:
            st.markdown("**⚠️ Danger signs found:**")
            for f in a["red_flags"]:
                st.markdown(f"- {f}")
        else:
            st.success("No danger signs found in the vital signs entered.")

        needs = alloc.required_resources(final, a["severe_flags"])
        st.info("Likely needs: " + ", ".join(alloc.RESOURCE_LABELS[n] for n in needs))

        if st.button("➕ Add this patient to the waiting list", type="primary"):
            st.session_state.queue.append(a)
            st.session_state.last_assessment = None
            st.success(f"Added {a['name']} to the waiting list.")
            st.rerun()


# ===========================================================================
# PAGE 2 - Waiting list & resource allocation
# ===========================================================================
elif page == "Waiting list":
    st.title("Waiting list and who gets seen first")
    queue = st.session_state.queue

    if not queue:
        st.info("No patients on the waiting list yet. Add some on the "
                "**Check a patient** page, or load examples on the **Quick demo** page.")
    else:
        st.write(f"There are **{len(queue)}** patients waiting. The system puts the "
                 "most urgent and the sickest first, then gives out the free resources.")

        result = alloc.allocate(queue, st.session_state.resources)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Patients waiting", len(queue))
        m2.metric("Can be seen now", result["n_admitted"])
        m3.metric("Still waiting for a resource", result["n_waiting"])
        left = result["resources_left"]
        m4.metric("Doctors left", left["doctors"])

        lc1, lc2, lc3 = st.columns(3)
        lc1.metric("ICU beds left", left["icu_beds"])
        lc2.metric("Ventilators left", left["ventilators"])
        lc3.metric("Ward beds left", left["ward_beds"])

        st.divider()
        st.subheader("Order of care")

        rows = []
        for x in result["results"]:
            rows.append({
                "Order": x["served_order"] if x["served_order"] else "-",
                "Patient": x["name"],
                "Urgency": x["effective_urgency"],
                "Warning score": x["risk"],
                "Status": "✅ See now" if x["status"] == "Admitted" else "⏳ Waiting",
                "Gets": ", ".join(x["assigned"]) if x["assigned"] else "-",
                "Waiting for": ", ".join(x["waiting_for"]) if x["waiting_for"] else "-",
                "Moved up?": "Yes" if x["escalated"] else "",
            })
        table = pd.DataFrame(rows)
        st.dataframe(
            table, use_container_width=True, hide_index=True,
            column_config={
                "Warning score": st.column_config.ProgressColumn(
                    "Warning score", min_value=0, max_value=100, format="%d"),
            },
        )

        with st.expander("See the danger signs for each patient"):
            for x in result["results"]:
                flags = ", ".join(x["red_flags"]) if x["red_flags"] else "none"
                st.markdown(f"**{x['name']}** ({x['effective_urgency']}): {flags}")

        st.divider()
        cby1, cby2 = st.columns(2)
        with cby1:
            names = [f"{i+1}. {p['name']}" for i, p in enumerate(queue)]
            to_remove = st.selectbox("Remove one patient", ["(none)"] + names)
            if st.button("Remove selected") and to_remove != "(none)":
                idx = names.index(to_remove)
                queue.pop(idx)
                st.rerun()
        with cby2:
            st.write("")
            st.write("")
            if st.button("🗑️ Clear the whole waiting list"):
                st.session_state.queue = []
                st.rerun()


# ===========================================================================
# PAGE 3 - Quick demo
# ===========================================================================
elif page == "Quick demo":
    st.title("Quick demo")
    st.write("Load real example patients from the dataset to see the system work "
             "without typing everything by hand.")

    n = st.slider("How many example patients?", 3, 20, 8)
    if st.button("Load example patients", type="primary"):
        raw = get_raw_data()
        X, y, medians = data_prep.build_feature_frame(raw)
        sample_idx = random.sample(list(X.index), min(n, len(X)))
        added = 0
        for j, idx in enumerate(sample_idx):
            patient = {col: float(X.at[idx, col]) for col in C.NUMERIC_FEATURES}
            for col in C.CATEGORICAL_FEATURES:
                patient[col] = int(X.at[idx, col])
            for f in C.SYMPTOM_FLAGS:
                patient[f] = int(X.at[idx, f])
            patient["name"] = f"Patient {j+1}"
            patient["complaint"] = str(raw.at[idx, "Chief_complain"]) \
                if "Chief_complain" in raw.columns else ""
            st.session_state.queue.append(assess(patient))
            added += 1
        st.success(f"Added {added} example patients to the waiting list. "
                   "Open the **Waiting list** page to see who gets seen first.")

    if st.session_state.queue:
        st.caption(f"The waiting list now has {len(st.session_state.queue)} patients.")


# ===========================================================================
# PAGE 4 - Model performance
# ===========================================================================
elif page == "How accurate is it?":
    st.title("How accurate is the model?")
    metrics = get_metrics()
    if not metrics:
        st.warning("No saved results found. Train the model first.")
    else:
        st.write("These numbers come from testing the model on patients it had "
                 "**never seen** during training.")
        m1, m2, m3 = st.columns(3)
        m1.metric("Correct on the test set", f"{metrics['accuracy']*100:.0f}%")
        m2.metric("Average across 5 re-tests",
                  f"{metrics['cv_mean']*100:.0f}%",
                  help="Cross-validation: trains and tests 5 times on different "
                       "splits to check the score is stable.")
        m3.metric("Patients in the data", metrics["n_total"])

        st.caption(f"Trained on {metrics['n_train']} patients, "
                   f"tested on {metrics['n_test']} patients.")

        st.divider()
        st.subheader("Where it agrees and disagrees")
        st.write("Rows are what the expert actually said; columns are what the "
                 "model guessed. The diagonal (top-left to bottom-right) is correct.")
        cm = pd.DataFrame(metrics["confusion_matrix"],
                          index=[f"Actually {c}" for c in metrics["classes"]],
                          columns=[f"Said {c}" for c in metrics["classes"]])
        st.dataframe(cm, use_container_width=True)

        st.subheader("Score for each urgency level")
        rep = metrics["report"]
        perf = pd.DataFrame({
            "Urgency": metrics["classes"],
            "Catches (recall)": [f"{rep[c]['recall']*100:.0f}%" for c in metrics["classes"]],
            "When it says this, it's right (precision)":
                [f"{rep[c]['precision']*100:.0f}%" for c in metrics["classes"]],
            "Patients tested": [int(rep[c]["support"]) for c in metrics["classes"]],
        })
        st.dataframe(perf, use_container_width=True, hide_index=True)

        st.subheader("What the model pays attention to most")
        imp = pd.DataFrame(metrics["feature_importances"][:12],
                           columns=["Feature", "Importance"])
        chart = (alt.Chart(imp).mark_bar().encode(
            x=alt.X("Importance:Q"),
            y=alt.Y("Feature:N", sort="-x", title=""),
        ).properties(height=350))
        st.altair_chart(chart, use_container_width=True)

        with st.expander("See the full decision rules (for the curious)"):
            st.code(metrics.get("tree_text", "not available"))


# ===========================================================================
# PAGE 5 - About
# ===========================================================================
elif page == "About":
    st.title("About TriageTech")
    st.markdown(
        """
**TriageTech** helps emergency staff decide two things, fast:

1. **How urgent is each patient?**  A *Decision Tree* (a kind of AI that learns
   simple yes/no rules) looks at the patient's vital signs and main problems and
   sorts them into **Critical**, **Medium**, or **Low**.

2. **Who gets the limited beds, ventilators and doctors first?**  A
   *priority queue* (the same idea as Uniform-Cost Search from class) always
   serves the most urgent and sickest patient next, until the resources run out.

#### A safety net you can see
On top of the model, the system runs simple danger checks on the vital signs
(for example *oxygen level very low*). If a danger sign is found, the patient is
moved up the list and the reason is shown on screen. Nothing is hidden.

#### Important
This is a **help for trained staff, not a replacement for them.** It is a class
project (COMP360-B). Always use your own judgement and hospital rules.

#### About the data
The model learned from a public emergency-department dataset (the KTAS triage
dataset) with about 1,200 real patient visits. Like all medical data it may not
represent every group of people equally, so results should be treated with care.

---
*Team TriageTech - Laiba Nouman & Sufyan Abbasi - COMP360-B, Spring 2026.*
        """
    )
