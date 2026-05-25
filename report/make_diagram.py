"""Generate the system workflow / architecture diagram for the final report."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from pathlib import Path

OUT = Path(__file__).resolve().parent / "architecture.png"

fig, ax = plt.subplots(figsize=(8.4, 10.2))
ax.set_xlim(0, 10)
ax.set_ylim(0, 21)
ax.axis("off")

BLUE = "#2c5f8a"
GREEN = "#2ca02c"
ORANGE = "#ff7f0e"
RED = "#d62728"
GREY = "#555555"


def box(y, text, color=BLUE, w=5.2, x=2.4, h=1.0, fs=11, text_color="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.12",
                                linewidth=1.5, edgecolor=color, facecolor=color, alpha=0.92))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color=text_color, weight="bold", wrap=True)


def arrow(y1, y2, x=5.0):
    ax.add_patch(FancyArrowPatch((x, y1), (x, y2), arrowstyle="-|>", mutation_scale=18,
                                 linewidth=1.8, color=GREY))


def sidelabel(y, text, color=GREY):
    ax.text(8.05, y, text, ha="left", va="center", fontsize=8.5, color=color, style="italic")


# Title
ax.text(5, 20.4, "TriageTech - System Workflow", ha="center", fontsize=15, weight="bold", color="#222")
ax.text(5, 19.8, "Two stages: classify urgency, then allocate resources",
        ha="center", fontsize=10, color=GREY)

# Stage banners
ax.text(0.2, 17.2, "STAGE 1\nClassification\n(Decision Tree)", ha="left", va="center",
        fontsize=9.5, color=BLUE, weight="bold")
ax.text(0.2, 7.6, "STAGE 2\nAllocation\n(Cost-based\nsearch / UCS)", ha="left", va="center",
        fontsize=9.5, color=ORANGE, weight="bold")

y = 18.2
box(y, "Patient data\n(vitals, symptoms, arrival, alertness)", color=BLUE, h=1.1)
sidelabel(y + 0.55, "nurse enters in plain English")

y -= 1.9; arrow(y + 1.9 - 0.0, y + 1.1)
box(y, "Data preprocessing\nclean text vitals - fill missing - map labels", color=BLUE, h=1.1)
sidelabel(y + 0.55, "+ engineered features\n(shock index, MAP, ...)")

y -= 1.9; arrow(y + 1.9, y + 1.1)
box(y, "Decision Tree model", color=BLUE, h=1.0)

y -= 1.8; arrow(y + 1.8, y + 1.0)
box(y, "Urgency prediction\nCritical  /  Medium  /  Low", color=GREEN, h=1.0)

y -= 1.8; arrow(y + 1.8, y + 1.0)
box(y, "Safety net (red-flag vital checks)\ncan escalate an under-rated patient", color=RED, h=1.1)
sidelabel(y + 0.55, "human oversight,\nshown on screen")

y -= 1.95; arrow(y + 1.95, y + 1.1)
box(y, "Priority assignment\nrisk score + urgency -> cost", color=ORANGE, h=1.1)

y -= 1.9; arrow(y + 1.9, y + 1.1)
box(y, "Resource allocation (priority queue)\nICU beds - ventilators - ward beds - doctors",
    color=ORANGE, h=1.1)
sidelabel(y + 0.55, "serve lowest-cost\n(sickest) first")

y -= 1.9; arrow(y + 1.9, y + 1.0)
box(y, "Final decision\nwho is seen now / who waits + for what", color="#444", h=1.0)

plt.tight_layout()
fig.savefig(OUT, dpi=150, bbox_inches="tight", facecolor="white")
print("saved", OUT)
