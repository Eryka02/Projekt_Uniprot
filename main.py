from pathlib import Path
import logging

from src.uniprot_enzyme_explorer.pipeline import (
    harvest_enzymes,
    load_uniprot_ids,
)
from src.uniprot_enzyme_explorer.reports import (
    export_to_csv,
    export_to_xlsx,
)
from src.uniprot_enzyme_explorer.charts import create_charts
from src.uniprot_enzyme_explorer.logger_setup import setup_logging

PROJECT_ROOT = Path(__file__).resolve().parent
INPUT_FILE = PROJECT_ROOT / "data" / "input_ids.txt"
REPORT_FILE = PROJECT_ROOT / "outputs" / "reports" / "enzyme_report.csv"
XLSX_REPORT_FILE = (
    PROJECT_ROOT / "outputs" / "reports" / "enzyme_report.xlsx"
)
CHARTS_DIRECTORY = PROJECT_ROOT / "outputs" / "charts"
LOG_FILE = PROJECT_ROOT / "logs" / "app.log"


def configure_logging():
    setup_logging(LOG_FILE)

    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        encoding="utf-8",
    )

def print_table(records):
    headers = [
        "ID UniProt",
        "Nazwa białka",
        "Organizm",
        "Długość",
        "Masa [Da]",
        "Numer EC",
        "Sekwencja",
    ]

    rows = []

    for record in records:
        rows.append([
            record.uniprot_id,
            record.protein_name,
            record.organism,
            str(record.sequence_length),
            str(record.molecular_weight),
            record.ec_number,
            record.sequence[:15] + "...",
        ])

    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    ]

    print(" | ".join(
        header.ljust(width)
        for header, width in zip(headers, widths)
    ))

    print("-+-".join("-" * width for width in widths))

    for row in rows:
        print(" | ".join(
            value.ljust(width)
            for value, width in zip(row, widths)
        ))


def main():
    configure_logging()
    logging.info("Uruchomiono UniProt Enzyme Explorer.")

    print("UniProt Enzyme Explorer")
    print("------------------------")

    try:
        uniprot_ids = load_uniprot_ids(INPUT_FILE)
    except OSError as error:
        print(f"Nie można odczytać pliku: {error}")
        logging.error("Błąd pliku wejściowego: %s", error)
        return

    if not uniprot_ids:
        print("Plik input_ids.txt nie zawiera identyfikatorów.")
        return

    print(f"Znaleziono identyfikatory: {len(uniprot_ids)}")
    print("Pobieranie danych z UniProt...")

    enzymes, errors = harvest_enzymes(uniprot_ids)

    if enzymes:
        print()
        print_table(enzymes)

        try:
            export_to_csv(enzymes, REPORT_FILE)
            relative_path = REPORT_FILE.relative_to(PROJECT_ROOT)
            print()
            print(f"Raport CSV zapisano: {relative_path}")
            logging.info("Zapisano raport CSV: %s", REPORT_FILE)
        except OSError as error:
            print(f"Nie udało się zapisać raportu CSV: {error}")
            logging.error("Błąd zapisu CSV: %s", error)

        try:
            export_to_xlsx(enzymes, XLSX_REPORT_FILE)
            relative_path = XLSX_REPORT_FILE.relative_to(PROJECT_ROOT)
            print(f"Raport XLSX zapisano: {relative_path}")
            logging.info("Zapisano raport XLSX: %s", XLSX_REPORT_FILE)
        except OSError as error:
            print(f"Nie udało się zapisać raportu XLSX: {error}")
            logging.error("Błąd zapisu XLSX: %s", error)

        try:
            chart_files = create_charts(
                enzymes,
                CHARTS_DIRECTORY,
            )

            print()
            print("Wykresy zapisano:")

            for chart_file in chart_files:
                relative_path = chart_file.relative_to(PROJECT_ROOT)
                print(f"- {relative_path}")

            logging.info("Utworzono wykresy.")

        except OSError as error:
            print(f"Nie udało się utworzyć wykresów: {error}")
            logging.error("Błąd tworzenia wykresów: %s", error)

    if errors:
        print()
        print("Nie udało się pobrać:")
        for error in errors:
            print(f"- {error}")

    print()
    print(f"Pobrano poprawnie: {len(enzymes)} z {len(uniprot_ids)}")


if __name__ == "__main__":
    main()