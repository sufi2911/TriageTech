import heapq

from . import config as C

# Default hospital resources (the nurse can change these on screen)
DEFAULT_RESOURCES = {
    "icu_beds": 2,
    "ventilators": 2,
    "ward_beds": 5,
    "doctors": 3,
}

RESOURCE_LABELS = {
    "icu_beds": "ICU bed",
    "ventilators": "Ventilator",
    "ward_beds": "Ward bed",
    "doctors": "Doctor",
}

# Lower rank = served earlier.
URGENCY_RANK = {"Critical": 0, "Medium": 1, "Low": 2}


# Risk score from vital signs (NEWS-style, simplified for teaching)
def _points(value, bands):
    
    if value is None:
        return 0
    for low, high, pts in bands:
        if low <= value <= high:
            return pts
    return 0


def compute_risk_score(p: dict) -> int:
    
    score = 0
    score += _points(p.get("HR"), [(0, 39, 3), (40, 50, 2), (51, 59, 1),
                                    (101, 110, 1), (111, 130, 2), (131, 400, 3)])
    score += _points(p.get("RR"), [(0, 7, 3), (8, 8, 2), (9, 11, 1),
                                    (21, 24, 2), (25, 30, 2), (31, 100, 3)])
    score += _points(p.get("SBP"), [(0, 89, 3), (90, 100, 2), (101, 110, 1),
                                     (221, 400, 2)])
    score += _points(p.get("Saturation"), [(0, 89, 3), (90, 92, 2), (93, 94, 1)])
    score += _points(p.get("BT"), [(0, 34.9, 3), (35.0, 36.0, 1),
                                    (38.1, 39.0, 1), (39.1, 50, 2)])
    mental = p.get("Mental", 1) or 1
    score += {1: 0, 2: 1, 3: 2, 4: 3}.get(int(mental), 0)

    # max possible raw points = 3+3+3+3+3+3 = 18  ->  scale to 0-100
    return int(round(min(score, 18) / 18 * 100))


def red_flags(p: dict):
    #Plain-English danger signs found in the vitals. Empty list = none.
    flags, severe = [], []

    def add(msg, is_severe):
        flags.append(msg)
        if is_severe:
            severe.append(msg)

    sat = p.get("Saturation")
    if sat is not None and sat < 90:
        add("Oxygen level is very low", True)
    elif sat is not None and sat < 94:
        add("Oxygen level is a little low", False)

    mental = int(p.get("Mental", 1) or 1)
    if mental >= 3:
        add("Patient is not properly responding", True)
    elif mental == 2:
        add("Patient is drowsy / only responds when spoken to", False)

    sbp = p.get("SBP")
    if sbp is not None and sbp < 90:
        add("Blood pressure is very low", True)

    rr = p.get("RR")
    if rr is not None and (rr > 30 or rr < 8):
        add("Breathing rate is dangerous", True)
    elif rr is not None and rr > 24:
        add("Breathing is fast", False)

    hr = p.get("HR")
    if hr is not None and (hr > 130 or hr < 40):
        add("Heart rate is dangerous", True)

    bt = p.get("BT")
    if bt is not None and (bt >= 39.5 or bt < 35):
        add("Body temperature is dangerous", True)

    nrs = p.get("NRS_pain")
    if nrs is not None and nrs >= 8:
        add("Patient is in severe pain", False)

    return flags, severe


def effective_urgency(model_urgency: str, severe_flags) -> str:
   
    if severe_flags and URGENCY_RANK[model_urgency] > URGENCY_RANK["Critical"]:
        return "Critical"
    return model_urgency


# What each urgency level needs
def required_resources(urgency: str, severe_flags) -> list:
    #Resources a patient needs, in priority order.
    if urgency == "Critical":
        needs = ["icu_beds", "doctors"]
        # only a struggling-to-breathe critical patient ties up a ventilator
        if any("Oxygen" in f or "Breathing" in f for f in severe_flags):
            needs.insert(1, "ventilators")
        return needs
    if urgency == "Medium":
        return ["ward_beds", "doctors"]
    return ["doctors"]  # Low: seen by a doctor, no bed needed


def allocation_cost(urgency: str, risk: int, order_index: int) -> float:
    #The UCS cost for a patient. Lower cost is popped (served) first.
    return URGENCY_RANK[urgency] * 1000 - risk + order_index * 0.001


def allocate(patients: list, resources: dict = None) -> dict:
    pool = dict(resources or DEFAULT_RESOURCES)
    start_pool = dict(pool)

    # 1) score everyone and build the min-heap (this is the "frontier")
    heap = []
    enriched = {}
    for i, p in enumerate(patients):
        risk = compute_risk_score(p)
        flags, severe = red_flags(p)
        eff = effective_urgency(p["urgency"], severe)
        enriched[i] = {
            **p,
            "risk": risk,
            "red_flags": flags,
            "severe_flags": severe,
            "model_urgency": p["urgency"],
            "effective_urgency": eff,
            "escalated": eff != p["urgency"],
        }
        cost = allocation_cost(eff, risk, i)
        heapq.heappush(heap, (cost, i))

    # 2) pop cheapest first and allocate what is available
    results = []
    served_order = 0
    while heap:
        cost, i = heapq.heappop(heap)
        info = enriched[i]
        needs = required_resources(info["effective_urgency"], info["severe_flags"])

        available = all(pool.get(r, 0) > 0 for r in needs)
        if available:
            for r in needs:
                pool[r] -= 1
            served_order += 1
            info["status"] = "Admitted"
            info["assigned"] = [RESOURCE_LABELS[r] for r in needs]
            info["waiting_for"] = []
            info["served_order"] = served_order
        else:
            info["status"] = "Waiting"
            info["assigned"] = []
            info["waiting_for"] = [RESOURCE_LABELS[r] for r in needs if pool.get(r, 0) <= 0]
            info["served_order"] = None
        info["cost"] = round(cost, 3)
        results.append(info)

    return {
        "results": results,
        "resources_start": start_pool,
        "resources_left": pool,
        "n_admitted": sum(1 for r in results if r["status"] == "Admitted"),
        "n_waiting": sum(1 for r in results if r["status"] == "Waiting"),
    }
