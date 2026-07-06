import json
import logging
from pathlib import Path

from src.uniprot_enzyme_explorer.models import EnzymeRecord


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"


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
                "reviewed_status": record.reviewed_status,
                "quality_score": record.quality_score,
                "hydrophobic_count": record.hydrophobic_count,
                "hydrophobic_percent": record.hydrophobic_percent,
                "cysteine_count": record.cysteine_count,
                "cysteine_percent": record.cysteine_percent,
                "most_common_amino_acid": record.most_common_amino_acid,
                "sequence_length_category": record.sequence_length_category,
                "interpretation": record.interpretation,
            }
        )

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(processed_data, file, ensure_ascii=False, indent=2)

    logging.info("Zapisano dane przetworzone: %s", output_file)