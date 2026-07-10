import json
import logging
from pathlib import Path

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

from src.uniprot_enzyme_explorer.models import EnzymeRecord
from src.uniprot_enzyme_explorer.sequence_qc import (
    prepare_non_redundant_set,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
FASTA_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "fasta"


def save_processed_records(records: list[EnzymeRecord]):
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    output_file = PROCESSED_DATA_DIR / "enzyme_records.json"

    processed_data = []

    for record in records:
        processed_data.append(
            {
                "uniprot_id": record.uniprot_id,
                "protein_name": record.protein_name,
                "organism": record.organism,
                "sequence_length": record.sequence_length,
                "molecular_weight": record.molecular_weight,
                "ec_number": record.ec_number,
                "sequence": record.sequence,
                "nucleotide_sequence": record.nucleotide_sequence,
                "nucleotide_source": record.nucleotide_source,
                "reviewed_status": record.reviewed_status,
                "hydrophobic_count": record.hydrophobic_count,
                "hydrophobic_percent": record.hydrophobic_percent,
                "cysteine_count": record.cysteine_count,
                "cysteine_percent": record.cysteine_percent,
                "most_common_amino_acid": record.most_common_amino_acid,
                "sequence_length_category": record.sequence_length_category,
                "interpretation": record.interpretation,
                "qc_status": record.qc_status,
                "duplicate_group": record.duplicate_group,
                "is_representative": record.is_representative,
                "representative_id": record.representative_id,
                "function_description": record.function_description,
                "catalytic_activity": record.catalytic_activity,
                "cofactors": record.cofactors,
                "subcellular_location": record.subcellular_location,
                "feature_summary": record.feature_summary,
                "structure_summary": record.structure_summary,
            }
        )

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(processed_data, file, ensure_ascii=False, indent=2)

    logging.info("Zapisano dane przetworzone: %s", output_file)


def export_all_enzymes_to_fasta(records: list[EnzymeRecord], output_dir=None) -> Path:
    fasta_dir = Path(output_dir) if output_dir else FASTA_OUTPUT_DIR
    fasta_dir.mkdir(parents=True, exist_ok=True)

    output_file = fasta_dir / "wszystkie_sekwencje_aminokwasowe.fasta"

    fasta_records = []

    for record in records:
        fasta_records.append(
            SeqRecord(
                Seq(record.sequence),
                id=record.uniprot_id,
                description=(
                    f"{record.protein_name} | {record.organism} | "
                    f"EC: {record.ec_number} | {record.reviewed_status}"
                ),
            )
        )

    with output_file.open("w", encoding="utf-8") as file:
        SeqIO.write(fasta_records, file, "fasta")

    logging.info("Zapisano wszystkie enzymy FASTA: %s", output_file)

    return output_file


def export_non_redundant_fasta(
    records: list[EnzymeRecord],
    output_dir=None,
) -> Path:
    fasta_dir = Path(output_dir) if output_dir else FASTA_OUTPUT_DIR
    fasta_dir.mkdir(parents=True, exist_ok=True)
    output_file = fasta_dir / "reprezentatywne_sekwencje_aminokwasowe.fasta"
    selected_records = prepare_non_redundant_set(records)

    fasta_records = [
        SeqRecord(
            Seq(record.sequence),
            id=record.uniprot_id,
            description=(
                f"{record.protein_name} | {record.organism} | "
                f"EC: {record.ec_number} | {record.reviewed_status}"
            ),
        )
        for record in selected_records
    ]
    with output_file.open("w", encoding="utf-8") as file:
        SeqIO.write(fasta_records, file, "fasta")
    logging.info(
        "Zapisano %s niedublujących się sekwencji FASTA: %s",
        len(fasta_records),
        output_file,
    )
    return output_file


def export_all_nucleotide_sequences_to_fasta(
    records: list[EnzymeRecord],
    output_dir=None,
) -> Path:
    fasta_dir = Path(output_dir) if output_dir else FASTA_OUTPUT_DIR
    fasta_dir.mkdir(parents=True, exist_ok=True)

    output_file = fasta_dir / "wszystkie_sekwencje_nukleotydowe.fasta"
    fasta_records = [
        SeqRecord(
            Seq(record.nucleotide_sequence),
            id=f"{record.uniprot_id}_nucleotide",
            description=(
                f"{record.protein_name} | {record.organism} | "
                f"EC: {record.ec_number} | źródło: {record.nucleotide_source}"
            ),
        )
        for record in records
        if record.nucleotide_sequence
    ]

    with output_file.open("w", encoding="utf-8") as file:
        SeqIO.write(fasta_records, file, "fasta")
    logging.info(
        "Zapisano %s sekwencji nukleotydowych FASTA: %s",
        len(fasta_records),
        output_file,
    )
    return output_file


def export_representative_nucleotide_sequences_to_fasta(
    records: list[EnzymeRecord],
    output_dir=None,
) -> Path:
    fasta_dir = Path(output_dir) if output_dir else FASTA_OUTPUT_DIR
    fasta_dir.mkdir(parents=True, exist_ok=True)

    output_file = fasta_dir / "reprezentatywne_sekwencje_nukleotydowe.fasta"
    selected_records = prepare_non_redundant_set(records)
    fasta_records = [
        SeqRecord(
            Seq(record.nucleotide_sequence),
            id=f"{record.uniprot_id}_nucleotide",
            description=(
                f"{record.protein_name} | {record.organism} | "
                f"EC: {record.ec_number} | źródło: {record.nucleotide_source}"
            ),
        )
        for record in selected_records
        if record.nucleotide_sequence
    ]

    with output_file.open("w", encoding="utf-8") as file:
        SeqIO.write(fasta_records, file, "fasta")
    logging.info(
        "Zapisano %s reprezentatywnych sekwencji nukleotydowych FASTA: %s",
        len(fasta_records),
        output_file,
    )
    return output_file
