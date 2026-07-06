import logging
import re
from pathlib import Path

from src.uniprot_enzyme_explorer.models import EnzymeRecord
from src.uniprot_enzyme_explorer.uniprot_client import (
    UniProtError,
    fetch_enzyme,
)
from src.uniprot_enzyme_explorer.analysis import rank_enzymes

def parse_uniprot_ids(text: str) -> list[str]:
    candidates = re.split(r"[\s,;]+", text.upper())
    uniprot_ids = []

    for candidate in candidates:
        candidate = candidate.strip()

        if candidate and candidate not in uniprot_ids:
            uniprot_ids.append(candidate)

    return uniprot_ids


def load_uniprot_ids(file_path: Path) -> list[str]:
    lines = []

    with file_path.open(encoding="utf-8") as file:
        for line in file:
            if not line.lstrip().startswith("#"):
                lines.append(line)

    return parse_uniprot_ids("".join(lines))

def load_uniprot_ids_from_files(
    file_paths: list[Path],
) -> list[str]:
    all_ids = []

    for file_path in file_paths:
        file_ids = load_uniprot_ids(file_path)

        for uniprot_id in file_ids:
            if uniprot_id not in all_ids:
                all_ids.append(uniprot_id)

    logging.info(
        "Wczytano %s identyfikatorów z %s plików.",
        len(all_ids),
        len(file_paths),
    )

    return all_ids


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

    ranked_enzymes = rank_enzymes(enzymes)

    logging.info(
        "Utworzono ranking enzymów dla %s rekordów.",
        len(ranked_enzymes),
    )

    return ranked_enzymes, errors