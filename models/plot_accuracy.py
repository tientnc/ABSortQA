import csv
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent.parent
ACCURACY_DIR = ROOT / "accuracy"

MODEL_COLORS = {
    "chemllm": "#4C78A8",
    "gemma": "#F58518",
    "gpt": "#54A24B",
    "llama": "#B279A2",
    "mistral": "#E45756",
    "qwen": "#72B7B2",
}


def read_percent_table(path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        label_field = reader.fieldnames[0]
        models = reader.fieldnames[1:]
        rows = []
        for row in reader:
            parsed = {label_field: row[label_field]}
            for model in models:
                parsed[model] = float(row[model].split("%", 1)[0])
            rows.append(parsed)
    return label_field, models, rows


def save_overall_accuracy(models, rows):
    overall = next(row for row in rows if row["Dataset Group"] == "OVERALL")
    values = sorted(((model, overall[model]) for model in models), key=lambda item: item[1])

    fig, ax = plt.subplots(figsize=(8, 4.8))
    labels = [model for model, _ in values]
    scores = [score for _, score in values]
    colors = [MODEL_COLORS[label] for label in labels]

    bars = ax.barh(labels, scores, color=colors)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Accuracy (%)")
    ax.set_title("Overall Model Accuracy")
    ax.grid(axis="x", linestyle="--", alpha=0.3)

    for bar, score in zip(bars, scores):
        ax.text(score + 1, bar.get_y() + bar.get_height() / 2, f"{score:.2f}%", va="center")

    fig.tight_layout()
    fig.savefig(ACCURACY_DIR / "overall_model_accuracy.png", dpi=200)
    plt.close(fig)


def save_dataset_accuracy(models, rows):
    dataset_rows = [row for row in rows if row["Dataset Group"] != "OVERALL"]
    groups = [row["Dataset Group"] for row in dataset_rows]
    x_positions = list(range(len(groups)))
    width = 0.12

    fig, ax = plt.subplots(figsize=(10, 5.6))
    for index, model in enumerate(models):
        offset = (index - (len(models) - 1) / 2) * width
        scores = [row[model] for row in dataset_rows]
        positions = [x + offset for x in x_positions]
        ax.bar(positions, scores, width=width, label=model, color=MODEL_COLORS[model])

    ax.set_xticks(x_positions)
    ax.set_xticklabels(groups, rotation=20, ha="right")
    ax.set_ylim(0, 100)
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("Accuracy by Dataset Group")
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    ax.legend(ncol=3, frameon=False)

    fig.tight_layout()
    fig.savefig(ACCURACY_DIR / "accuracy_by_dataset_group.png", dpi=200)
    plt.close(fig)


def save_functional_group_heatmap(models, rows):
    groups = [row["Functional Group"] for row in rows]
    values = [[row[model] for model in models] for row in rows]

    fig, ax = plt.subplots(figsize=(9, 8))
    image = ax.imshow(values, cmap="YlGnBu", vmin=0, vmax=100, aspect="auto")

    ax.set_xticks(range(len(models)))
    ax.set_xticklabels(models)
    ax.set_yticks(range(len(groups)))
    ax.set_yticklabels(groups)
    ax.set_title("Accuracy by Functional Group")

    for row_index, row in enumerate(values):
        for col_index, score in enumerate(row):
            color = "white" if score >= 70 else "black"
            ax.text(col_index, row_index, f"{score:.0f}", ha="center", va="center", fontsize=8, color=color)

    cbar = fig.colorbar(image, ax=ax)
    cbar.set_label("Accuracy (%)")
    fig.tight_layout()
    fig.savefig(ACCURACY_DIR / "accuracy_by_functional_group_heatmap.png", dpi=200)
    plt.close(fig)


def main():
    dataset_label, models, dataset_rows = read_percent_table(ACCURACY_DIR / "accuracy_by_dataset_with_fracs.csv")
    fg_label, fg_models, fg_rows = read_percent_table(ACCURACY_DIR / "accuracy_by_functional_group_with_fracs.csv")

    if dataset_label != "Dataset Group" or fg_label != "Functional Group" or models != fg_models:
        raise ValueError("Accuracy CSVs have unexpected headers.")

    save_overall_accuracy(models, dataset_rows)
    save_dataset_accuracy(models, dataset_rows)
    save_functional_group_heatmap(models, fg_rows)


if __name__ == "__main__":
    main()
