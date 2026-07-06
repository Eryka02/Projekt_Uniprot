import json
import logging
from pathlib import Path

import requests

from src.uniprot_enzyme_explorer.models import EnzymeRecord


BASE_URL = "https://rest.uniprot.org/uniprotkb"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

class UniProtError(Exception):
    pass
def save_raw_uniprot_data(uniprot_id: str, data: dict):
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    raw_file = RAW_DATA_DIR / f"{uniprot_id}.json"

    with open(raw_file, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    logging.info("Zapisano surowe dane UniProt: %s", raw_file)

def fetch_enzyme(uniprot_id: str) -> EnzymeRecord:
    url = f"{BASE_URL}/{uniprot_id}.json"

    try:
        response = requests.get(url, timeout=30)

        if response.status_code == 404:
            raise UniProtError(
                f"Nie znaleziono rekordu UniProt: {uniprot_id}"
            )

        response.raise_for_status()
        data = response.json()
        save_raw_uniprot_data(uniprot_id, data)

        entry_type = data.get("entryType", "").lower()

        if "unreviewed" in entry_type:
            reviewed_status = "unreviewed"
        elif "reviewed" in entry_type:
            reviewed_status = "reviewed"
        else:
            reviewed_status = "Brak danych"

    except requests.Timeout as error:
        raise UniProtError("UniProt nie odpowiedział w wymaganym czasie.") from error

    except requests.RequestException as error:
        raise UniProtError(f"Błąd połączenia z UniProt: {error}") from error

    protein_description = data["proteinDescription"]
    recommended_name = protein_description["recommendedName"]

    protein_name = recommended_name["fullName"]["value"]

    ec_numbers = recommended_name.get("ecNumbers", [])
    ec_number = ", ".join(
        item["value"] for item in ec_numbers
    ) or "Brak"

    sequence_data = data["sequence"]

    return EnzymeRecord(
        uniprot_id=data["primaryAccession"],
        protein_name=protein_name,
        organism=data["organism"]["scientificName"],
        molecular_weight=sequence_data["molWeight"],
        ec_number=ec_number,
        sequence=sequence_data["value"],
        reviewed_status=reviewed_status,
    )