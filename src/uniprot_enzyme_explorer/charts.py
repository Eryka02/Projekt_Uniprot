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


def create_charts(
    records: list[EnzymeRecord],
    output_directory: Path,
) -> list[Path]:
    output_directory.mkdir(parents=True, exist_ok=True)

    labels = [record.uniprot_id for record in records]

    lengths = [
        record.sequence_length
        for record in records
    ]

    masses_kda = [
        record.molecular_weight / 1000
        for record in records
    ]

    length_chart = output_directory / "sequence_lengths.png"
    mass_chart = output_directory / "molecular_weights.png"

    _save_bar_chart(
        labels=labels,
        values=lengths,
        title="Długość sekwencji enzymów",
        y_label="Liczba aminokwasów",
        color="#2F6690",
        value_format="%.0f",
        output_file=length_chart,
    )

    _save_bar_chart(
        labels=labels,
        values=masses_kda,
        title="Masa cząsteczkowa enzymów",
        y_label="Masa [kDa]",
        color="#3A7D44",
        value_format="%.1f",
        output_file=mass_chart,
    )

    return [length_chart, mass_chart]