from pathlib import Path

import matplotlib.pyplot as plt


def _chart_size(item_count: int) -> tuple[float, float]:
    width = min(12.0, max(9.5, 6.0 + item_count * 0.28))
    return width, 6.2


def _label_options(item_count: int) -> dict:
    if item_count > 14:
        return {
            "rotation": 55,
            "ha": "right",
            "fontsize": 7,
        }
    if item_count > 8:
        return {
            "rotation": 40,
            "ha": "right",
            "fontsize": 8,
        }
    return {
        "rotation": 0,
        "ha": "center",
        "fontsize": 9,
    }


def _save_bar_chart(
    labels,
    values,
    title: str,
    y_label: str,
    color: str,
    output_file: Path,
):
    item_count = len(labels)
    figure, axes = plt.subplots(figsize=_chart_size(item_count))
    positions = range(item_count)

    axes.bar(
        positions,
        values,
        color=color,
        edgecolor="#333333",
        linewidth=0.5,
    )

    axes.set_title(title, fontsize=13, pad=12)
    axes.set_xlabel("Identyfikator UniProt", labelpad=10)
    axes.set_ylabel(y_label)
    axes.set_xticks(list(positions))
    axes.set_xticklabels(labels, **_label_options(item_count))
    axes.grid(axis="y", linestyle="--", alpha=0.3)
    axes.set_axisbelow(True)
    axes.margins(x=0.01)

    figure.tight_layout(pad=1.5)
    figure.savefig(output_file, dpi=90)
    plt.close(figure)


def create_charts(enzymes, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    chart_files = []

    enzyme_ids = [
        enzyme.uniprot_id
        for enzyme in enzymes
    ]

    def save_bar_chart(values, title, ylabel, filename, color):
        chart_path = output_dir / filename
        _save_bar_chart(
            enzyme_ids,
            values,
            title,
            ylabel,
            color,
            chart_path,
        )
        chart_files.append(chart_path)

    save_bar_chart(
        [enzyme.sequence_length for enzyme in enzymes],
        "Porównanie długości sekwencji enzymów",
        "Długość sekwencji",
        "sequence_lengths.png",
        "#4c78a8",
    )

    save_bar_chart(
        [enzyme.molecular_weight for enzyme in enzymes],
        "Porównanie masy cząsteczkowej enzymów",
        "Masa cząsteczkowa [Da]",
        "molecular_weights.png",
        "#f58518",
    )

    save_bar_chart(
        [enzyme.cysteine_count for enzyme in enzymes],
        "Liczba cystein w sekwencjach",
        "Liczba cystein",
        "cysteine_counts.png",
        "#54a24b",
    )

    save_bar_chart(
        [enzyme.hydrophobic_percent for enzyme in enzymes],
        "Udział aminokwasów hydrofobowych",
        "Aminokwasy hydrofobowe [%]",
        "hydrophobic_percent.png",
        "#b279a2",
    )

    reviewed_count = sum(
        1 for enzyme in enzymes
        if enzyme.reviewed_status == "reviewed"
    )
    unreviewed_count = sum(
        1 for enzyme in enzymes
        if enzyme.reviewed_status == "unreviewed"
    )

    status_chart_path = output_dir / "reviewed_status.png"
    figure, axes = plt.subplots(figsize=(7.5, 5.8))
    axes.bar(
        ["reviewed", "unreviewed"],
        [reviewed_count, unreviewed_count],
        color=["#59a14f", "#e15759"],
        edgecolor="#333333",
        linewidth=0.5,
    )
    axes.set_title("Liczba rekordów reviewed i unreviewed", fontsize=13, pad=12)
    axes.set_ylabel("Liczba rekordów")
    axes.grid(axis="y", linestyle="--", alpha=0.3)
    axes.set_axisbelow(True)
    figure.tight_layout(pad=1.5)
    figure.savefig(status_chart_path, dpi=90)
    plt.close(figure)

    chart_files.append(status_chart_path)

    return chart_files
