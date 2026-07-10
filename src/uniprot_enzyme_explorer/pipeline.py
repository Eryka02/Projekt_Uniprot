import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from src.uniprot_enzyme_explorer.analysis import analyze_enzymes
from src.uniprot_enzyme_explorer.models import EnzymeRecord
from src.uniprot_enzyme_explorer.sequence_qc import (
    find_duplicate_ids,
    group_identical_sequences,
)
from src.uniprot_enzyme_explorer.uniprot_client import (
    UniProtError,
    fetch_enzyme,
)


MAX_DOWNLOAD_WORKERS = 5


def parse_uniprot_ids(text: str) -> list[str]:
    candidates = re.split(r"[\s,;]+", text.upper())
    return [
        candidate.strip()
        for candidate in candidates
        if candidate.strip()
    ]


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
        all_ids.extend(file_ids)

    logging.info(
        "Wczytano %s identyfikatorów z %s plików.",
        len(all_ids),
        len(file_paths),
    )

    return all_ids


def harvest_enzymes(
    uniprot_ids: list[str],
) -> tuple[list[EnzymeRecord], list[str]]:
    errors = []
    duplicate_ids = find_duplicate_ids(uniprot_ids)
    unique_ids = list(dict.fromkeys(uniprot_ids))
    enzymes_by_index = [None] * len(unique_ids)

    logging.info(
        "Wykryto %s powtórzone identyfikatory; pobieranie %s unikalnych ID.",
        len(duplicate_ids),
        len(unique_ids),
    )

    worker_count = min(MAX_DOWNLOAD_WORKERS, len(unique_ids)) or 1

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_to_record = {
            executor.submit(fetch_enzyme, uniprot_id): (index, uniprot_id)
            for index, uniprot_id in enumerate(unique_ids)
        }

        for future in as_completed(future_to_record):
            index, uniprot_id = future_to_record[future]
            logging.info("Pobieranie rekordu: %s", uniprot_id)

            try:
                enzyme = future.result()
                enzymes_by_index[index] = enzyme
                logging.info("Pobrano rekord: %s", uniprot_id)

            except UniProtError as error:
                message = f"{uniprot_id}: {error}"
                errors.append(message)
                logging.warning(message)

            except Exception as error:
                logging.exception("Nieoczekiwany błąd pobierania rekordu.")
                message = f"{uniprot_id}: {error}"
                errors.append(message)

    enzymes = [
        enzyme
        for enzyme in enzymes_by_index
        if enzyme is not None
    ]

    analyzed_enzymes = analyze_enzymes(enzymes)
    duplicate_groups = group_identical_sequences(analyzed_enzymes)
    logging.info(
        "Przeanalizowano %s rekordów; znaleziono %s grup duplikatów.",
        len(analyzed_enzymes),
        len(duplicate_groups),
    )

    return analyzed_enzymes, errors
