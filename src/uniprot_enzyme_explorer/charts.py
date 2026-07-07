from pathlib import Path

import matplotlib.pyplot as plt

from src.uniprot_enzyme_explorer.models import EnzymeRecord


def _save_bar_chart(
    labels,
    values,
    title: str,
    y_label: str,
    color: str,
    value_format: str,
    output_file: Path,
):
    figure, axes = plt.subplots(figsize=(8, 5))

    bars = axes.bar(
        labels,
        values,
        color=color,
        edgecolor="#333333",
    )

    axes.bar_label(
        bars,
        fmt=value_format,
        padding=3,
    )

    axes.set_title(title)
    axes.set_xlabel("Identyfikator UniProt")
    axes.set_ylabel(y_label)
    axes.grid(axis="y", linestyle="--", alpha=0.3)
    axes.set_axisbelow(True)

    figure.tight_layout()
    figure.savefig(output_file, dpi=150)
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

        plt.figure(figsize=(9, 5))
        plt.bar(enzyme_ids, values, color=color)
        plt.title(title)
        plt.xlabel("Identyfikator UniProt")
        plt.ylabel(ylabel)
        plt.tight_layout()
        plt.savefig(chart_path)
        plt.close()

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
        [enzyme.quality_score for enzyme in enzymes],
        "Ranking jakości rekordów UniProt",
        "Quality score",
        "quality_scores.png",
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

    plt.figure(figsize=(6, 5))
    plt.bar(
        ["reviewed", "unreviewed"],
        [reviewed_count, unreviewed_count],
        color=["#59a14f", "#e15759"],
    )
    plt.title("Liczba rekordów reviewed i unreviewed")
    plt.ylabel("Liczba rekordów")
    plt.tight_layout()
    plt.savefig(status_chart_path)
    plt.close()

    chart_files.append(status_chart_path)

    return chart_files