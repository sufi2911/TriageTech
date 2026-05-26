import matplotlib.pyplot as plt
import numpy as np

from src import config as C
from src import model


def print_confusion_matrix(cm, classes) -> None:
    """Pretty-print a confusion matrix to the terminal."""
    width = max(len(c) for c in classes) + 2
    header = " " * (width + 8) + "  ".join(f"Said {c:<{width}}" for c in classes)
    print(header)
    for row_label, row in zip(classes, cm):
        cells = "  ".join(f"{v:<{width + 4}}" for v in row)
        print(f"Actual {row_label:<{width}}{cells}")


def plot_confusion_matrix(cm, classes) -> None:
    """Draw the confusion matrix as a colour-coded heat map."""
    cm = np.array(cm)
    fig, ax = plt.subplots(figsize=(5.5, 4.6))
    im = ax.imshow(cm, cmap="Blues")
    fig.colorbar(im, fraction=0.046, pad=0.04)

    ax.set_xticks(range(len(classes)))
    ax.set_yticks(range(len(classes)))
    ax.set_xticklabels([f"Said\n{c}" for c in classes])
    ax.set_yticklabels([f"Actually\n{c}" for c in classes])
    ax.set_xlabel("Predicted label")
    ax.set_ylabel("True label")
    ax.set_title("Confusion matrix (test set)", weight="bold")

    # Write the count inside each cell — switch text colour on dark squares.
    threshold = cm.max() * 0.5
    for i in range(len(classes)):
        for j in range(len(classes)):
            ax.text(j, i, int(cm[i, j]), ha="center", va="center",
                    color="white" if cm[i, j] > threshold else "black",
                    fontsize=14, weight="bold")

    fig.tight_layout()


def plot_classification_report(report, classes) -> None:
    """Draw precision / recall / f1-score as a grouped bar chart."""
    metrics_to_plot = ["precision", "recall", "f1-score"]
    values = np.array([[report[c][m] for m in metrics_to_plot] for c in classes])

    x = np.arange(len(classes))
    bar_width = 0.25
    colors = ["#4c78a8", "#f58518", "#54a24b"]

    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    for i, metric in enumerate(metrics_to_plot):
        offset = (i - 1) * bar_width
        bars = ax.bar(x + offset, values[:, i], bar_width,
                      label=metric, color=colors[i])
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                    f"{bar.get_height():.2f}", ha="center", va="bottom", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(classes)
    ax.set_ylim(0, 1.1)
    ax.set_ylabel("Score (0 - 1)")
    ax.set_title("Classification report by urgency class", weight="bold")
    ax.legend(loc="lower right")
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    fig.tight_layout()


def main() -> None:
    metrics = model.load_metrics()
    if not metrics:
        print("No saved model found. Run:  python -m src.model")
        return

    classes = metrics["classes"]

    print(f"Test accuracy : {metrics['accuracy'] * 100:.1f}%")
    print(f"5-fold CV     : {metrics['cv_mean'] * 100:.1f}% "
          f"(+/- {metrics['cv_std'] * 100:.1f}%)")
    print(f"Trained on    : {metrics['n_train']} patients")
    print(f"Tested on     : {metrics['n_test']} patients")

    print("\nClassification report")
    print("-" * 60)
    print(metrics["report_text"])

    print("Confusion matrix (rows = actual, columns = predicted)")
    print("-" * 60)
    print_confusion_matrix(metrics["confusion_matrix"], classes)

    plot_confusion_matrix(metrics["confusion_matrix"], classes)
    plot_classification_report(metrics["report"], classes)
    print("\nClose the chart windows to exit.")
    plt.show()


if __name__ == "__main__":
    main()
