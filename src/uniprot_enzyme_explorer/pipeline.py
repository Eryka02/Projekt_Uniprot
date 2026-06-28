import logging
from pathlib import Path

from src.uniprot_enzyme_explorer.models import EnzymeRecord
from src.uniprot_enzyme_explorer.uniprot_client import (
    UniProtError,
    fetch_enzyme,
)


def load_uniprot_ids(file_path: Path) -> list[str]:
    uniprot_ids = []

    with file_path.open(encoding="utf-8") as file:
        for line in file:
            uniprot_id = line.strip()

            if (
                uniprot_id
                and not uniprot_id.startswith("#")
                and uniprot_id not in uniprot_ids
            ):
                uniprot_ids.append(uniprot_id)

    return uniprot_ids


def harvest_enzymes(
    uniprot_ids: list[str],
) -> tuple[list[EnzymeRecord], list[str]]:
    enzymes = []
    errors = []

    for uniprot_id in uniprot_ids:
        logging.info("Pobieranie rekordu: %s", uniprot_id)

        try:
            enzyme = fetch_enzyme(uniprot_id)
            enzymes.append(enzyme)
            logging.info("Pobrano rekord: %s", uniprot_id)

        except UniProtError as error:
            message = f"{uniprot_id}: {error}"
            errors.append(message)
            logging.warning(message)

    return enzymes, errors