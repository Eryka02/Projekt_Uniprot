import csv
from pathlib import Path

from src.uniprot_enzyme_explorer.models import EnzymeRecord


def export_to_csv(
    records: list[EnzymeRecord],
    output_file: Path,
) -> Path:
    output_file.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "uniprot_id",
        "protein_name",
        "organism",
        "sequence_length",
        "molecular_weight_da",
        "ec_number",
        "sequence",
    ]

    with output_file.open(
        mode="w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            delimiter=";",
        )

        writer.writeheader()

        for record in records:
            writer.writerow({
                "uniprot_id": record.uniprot_id,
                "protein_name": record.protein_name,
                "organism": record.organism,
                "sequence_length": record.sequence_length,
                "molecular_weight_da": record.molecular_weight,
                "ec_number": record.ec_number,
                "sequence": record.sequence,
            })

    return output_file