from collections import defaultdict

from src.uniprot_enzyme_explorer.ec_classes import get_ec_class_name


def decision_for(enzyme, input_count: int = 0) -> str:
    if not enzyme.sequence:
        return "brak sekwencji"
    if not enzyme.is_representative:
        return "duplikat sekwencji - pominięty"
    return "zostaje w FASTA"


def input_duplicate_text(input_count: int) -> str:
    if input_count > 1:
        return (
            f"wpisane {input_count} razy w plikach/polu; "
            "aplikacja pokazuje ten rekord raz"
        )

    return "brak powtórzenia tego ID"


def sequence_comparison_text(enzyme) -> str:
    if not enzyme.sequence:
        return "brak sekwencji do porównania"

    if not enzyme.duplicate_group:
        return "nie znaleziono innego rekordu z identyczną sekwencją"

    if enzyme.is_representative:
        return f"reprezentant grupy {enzyme.duplicate_group}"

    return f"duplikat identycznej sekwencji z grupy {enzyme.duplicate_group}"


def table_check_status(enzyme, input_count: int = 0) -> str:
    parts = []

    if input_count > 1:
        parts.append(f"ID {input_count}x")

    if not enzyme.sequence:
        parts.append("brak sekwencji")
    elif enzyme.duplicate_group:
        status = "reprezentant" if enzyme.is_representative else "duplikat"
        parts.append(f"sekw. {status}")
    else:
        parts.append("sekw. unikalna")

    return "; ".join(parts)


def format_interpretation_text(enzyme, input_count: int = 0) -> str:
    lines = [
        enzyme.interpretation,
        "",
        f"Decyzja programu: {decision_for(enzyme, input_count)}.",
        f"Powtórzenie ID wejściowego: {input_duplicate_text(input_count)}.",
        f"Porównanie identycznych sekwencji: {sequence_comparison_text(enzyme)}.",
    ]

    if enzyme.duplicate_group:
        lines.extend(
            [
                f"Grupa identycznej sekwencji: {enzyme.duplicate_group}.",
                (
                    "Reprezentant grupy: "
                    f"{enzyme.representative_id or enzyme.uniprot_id}."
                ),
            ]
        )

    return "\n".join(lines)


def format_protein_fasta_header(enzyme) -> str:
    return (
        f">{enzyme.uniprot_id}_protein {enzyme.protein_name} | "
        f"{enzyme.organism} | EC: {enzyme.ec_number} | "
        f"{enzyme.reviewed_status}"
    )


def format_nucleotide_fasta_header(enzyme) -> str:
    return (
        f">{enzyme.uniprot_id}_nucleotide {enzyme.protein_name} | "
        f"{enzyme.organism} | EC: {enzyme.ec_number} | "
        f"źródło: {enzyme.nucleotide_source}"
    )


def missing_nucleotide_message(enzyme) -> str:
    return (
        "Nie udało się pobrać sekwencji nukleotydowej dla tego rekordu.\n"
        f"Źródło/uwaga: {enzyme.nucleotide_source}"
    )


def wrap_sequence(sequence: str, line_length: int = 70) -> str:
    return "\n".join(
        sequence[index:index + line_length]
        for index in range(0, len(sequence), line_length)
    )


def build_duplicates_text(
    enzymes,
    input_duplicate_count: int,
    unique_input_count: int,
    input_duplicate_ids: dict[str, int] | None = None,
    selected_enzyme=None,
) -> str:
    input_duplicate_ids = input_duplicate_ids or {}
    lines = [
        "1. Powtórzone ID w danych wejściowych",
        f"Powtórzone wpisy: {input_duplicate_count}",
        f"Unikalne ID pobierane z UniProt: {unique_input_count}",
        "",
    ]

    if input_duplicate_ids:
        for identifier, count in input_duplicate_ids.items():
            lines.append(
                f"- {identifier}: wpisane {count} razy, pobrane i pokazane raz"
            )
    else:
        lines.append("Brak powtórzonych ID w danych wejściowych.")

    lines.extend(["", "2. Identyczne sekwencje białkowe (100%)", ""])

    duplicate_groups = {}
    for enzyme in enzymes:
        if enzyme.duplicate_group:
            duplicate_groups.setdefault(enzyme.duplicate_group, []).append(enzyme)

    if duplicate_groups:
        for group_id, records in duplicate_groups.items():
            representative = next(
                (
                    record
                    for record in records
                    if record.is_representative
                ),
                records[0],
            )
            lines.append("")
            lines.append(f"{group_id}")
            lines.append(f"  Reprezentant: {representative.uniprot_id}")
            for record in records:
                status = "zostaje" if record.is_representative else "duplikat"
                lines.append(f"  - {record.uniprot_id}: {status}")
    else:
        lines.append("Nie wykryto identycznych sekwencji w pobranych rekordach.")
        lines.append(
            "To nie znaczy, że enzymy nie są podobne; ta część sprawdza "
            "tylko sekwencje identyczne znak po znaku."
        )

    lines.extend(["", "3. Rekordy z tym samym numerem EC", ""])
    ec_groups = build_ec_groups(enzymes)

    if ec_groups:
        lines.append(
            "Ten sam EC oznacza podobny typ reakcji enzymatycznej, "
            "ale nie musi oznaczać identycznej sekwencji."
        )
        for ec_number, records in ec_groups.items():
            lines.append("")
            lines.append(f"EC {ec_number}")
            for record in records:
                lines.append(f"  - {record.uniprot_id}: {record.protein_name}")
    else:
        lines.append(
            "Nie ma kilku pobranych rekordów z tym samym dokładnym numerem EC."
        )

    if selected_enzyme and selected_enzyme.duplicate_group:
        lines.append("")
        lines.append(
            f"Zaznaczony rekord należy do grupy "
            f"{selected_enzyme.duplicate_group}."
        )

    return "\n".join(lines)


def split_ec_numbers(ec_number: str) -> list[str]:
    return [
        value.strip()
        for value in (ec_number or "").split(",")
        if value.strip() and value.strip().lower() not in {"brak", "brak danych"}
    ]


def build_ec_groups(enzymes) -> dict[str, list]:
    groups = defaultdict(list)

    for enzyme in enzymes:
        for ec_number in split_ec_numbers(enzyme.ec_number):
            groups[ec_number].append(enzyme)

    return {
        ec_number: records
        for ec_number, records in groups.items()
        if len(records) > 1
    }


def format_full_details(enzyme, input_count: int = 0) -> str:
    return (
        f"Identyfikator UniProt: {enzyme.uniprot_id}\n"
        f"Powtórzenie ID wejściowego: {input_duplicate_text(input_count)}\n"
        f"Porównanie identycznych sekwencji: {sequence_comparison_text(enzyme)}\n"
        f"Nazwa białka: {enzyme.protein_name}\n"
        f"Organizm: {enzyme.organism}\n"
        f"Numer EC: {enzyme.ec_number}\n"
        f"Rodzaj enzymu: {get_ec_class_name(enzyme.ec_number)}\n"
        f"Masa cząsteczkowa: {enzyme.molecular_weight}\n"
        f"Długość sekwencji: {enzyme.sequence_length}\n"
        f"Status rekordu: {enzyme.reviewed_status}\n\n"
        f"Statystyki sekwencji:\n"
        f"- aminokwasy hydrofobowe: {enzyme.hydrophobic_count}\n"
        f"- procent aminokwasów hydrofobowych: "
        f"{enzyme.hydrophobic_percent}%\n"
        f"- liczba cystein: {enzyme.cysteine_count}\n"
        f"- procent cystein: {enzyme.cysteine_percent}%\n"
        f"- najczęstszy aminokwas: {enzyme.most_common_amino_acid}\n"
        "\n"
        f"Informacje z UniProt:\n"
        f"- funkcja: {enzyme.function_description}\n"
        f"- reakcja: {enzyme.catalytic_activity}\n"
        f"- kofaktory: {enzyme.cofactors}\n"
        f"- lokalizacja: {enzyme.subcellular_location}\n"
        f"- cechy sekwencji: {enzyme.feature_summary}\n"
        "\n"
        f"Interpretacja:\n{enzyme.interpretation}\n\n"
        f"Sekwencja aminokwasowa:\n{enzyme.sequence}"
    )
