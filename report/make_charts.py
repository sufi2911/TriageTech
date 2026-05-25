"""Generate confusion-matrix and feature-importance figures for the report."""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

HERE = Path(__file__).resolve().parent
M = json.loads((HERE.parent / "models" / "metrics.json").read_text())

# ---- confusion matrix ----
cm = np.array(M["confusion_matrix"])
classes = M["classes"]
fig, ax = plt.subplots(figsize=(5.2, 4.4))
im = ax.imshow(cm, cmap="Blues")
ax.set_xticks(range(len(classes)), labels=[f"Said\n{c}" for c in classes])
ax.set_yticks(range(len(classes)), labels=[f"Actually\n{c}" for c in classes])
for i in range(len(classes)):
    for j in range(len(classes)):
        ax.text(j, i, cm[i, j], ha="center", va="center",
                color="white" if cm[i, j] > cm.max() * 0.5 else "black",
                fontsize=14, weight="bold")
ax.set_title("Confusion matrix (test set)", weight="bold")
fig.colorbar(im, fraction=0.046, pad=0.04)
plt.tight_layout()
fig.savefig(HERE / "confusion_matrix.png", dpi=150, facecolor="white")

# ---- feature importance ----
imp = [t for t in M["feature_importances"] if t[1] > 0][:10][::-1]
names = [t[0] for t in imp]
vals = [t[1] for t in imp]
fig, ax = plt.subplots(figsize=(6.4, 4.2))
ax.barh(names, vals, color="#2c5f8a")
ax.set_xlabel("Importance")
ax.set_title("What the Decision Tree relies on most", weight="bold")
plt.tight_layout()
fig.savefig(HERE / "feature_importance.png", dpi=150, facecolor="white")
print("charts saved")
