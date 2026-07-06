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
            }
        )

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(processed_data, file, ensure_ascii=False, indent=2)

    logging.info("Zapisano dane przetworzone: %s", output_file)