from collections import Counter


HYDROPHOBIC_AMINO_ACIDS = set("AILMFWVPG")


def has_value(value) -> bool:
    return value not in (None, "", "Brak", "Brak danych")


def calculate_sequence_stats(sequence: str) -> dict:
    if not sequence:
        return {
            "hydrophobic_count": 0,
            "hydrophobic_percent": 0.0,
            "cysteine_count": 0,
            "cysteine_percent": 0.0,
            "most_common_amino_acid": "Brak",
            "sequence_length_category": "Brak",
        }

    sequence = sequence.upper()
    sequence_length = len(sequence)

    hydrophobic_count = sum(
        1 for amino_acid in sequence
        if amino_acid in HYDROPHOBIC_AMINO_ACIDS
    )

    cysteine_count = sequence.count("C")

    amino_acid_counts = Counter(sequence)
    most_common_amino_acid = amino_acid_counts.most_common(1)[0][0]

    hydrophobic_percent = round(
        hydrophobic_count / sequence_length * 100,
        2,
    )
    cysteine_percent = round(
        cysteine_count / sequence_length * 100,
        2,
    )

    if sequence_length < 100:
        length_category = "krótkie"
    elif sequence_length <= 500:
        length_category = "średnie"
    else:
        length_category = "długie"

    return {
        "hydrophobic_count": hydrophobic_count,
        "hydrophobic_percent": hydrophobic_percent,
        "cysteine_count": cysteine_count,
        "cysteine_percent": cysteine_percent,
        "most_common_amino_acid": most_common_amino_acid,
        "sequence_length_category": length_category,
    }


def generate_interpretation(enzyme) -> str:
    parts = [
        f"Rekord {enzyme.uniprot_id}",
    ]

    if enzyme.reviewed_status == "reviewed":
        parts.append("jest rekordem reviewed/Swiss-Prot")
    else:
        parts.append("jest rekordem unreviewed/TrEMBL")

    if has_value(enzyme.ec_number):
        parts.append("posiada numer EC")
    else:
        parts.append("nie posiada numeru EC")

    if has_value(enzyme.sequence):
        parts.append("posiada sekwencję aminokwasową")

    return ", ".join(parts) + "."


def analyze_enzyme(enzyme):
    sequence_stats = calculate_sequence_stats(enzyme.sequence)

    enzyme.hydrophobic_count = sequence_stats["hydrophobic_count"]
    enzyme.hydrophobic_percent = sequence_stats["hydrophobic_percent"]
    enzyme.cysteine_count = sequence_stats["cysteine_count"]
    enzyme.cysteine_percent = sequence_stats["cysteine_percent"]
    enzyme.most_common_amino_acid = sequence_stats["most_common_amino_acid"]
    enzyme.sequence_length_category = sequence_stats[
        "sequence_length_category"
    ]

    enzyme.interpretation = generate_interpretation(enzyme)

    return enzyme


def analyze_enzymes(enzymes):
    """Oblicz statystyki bez oceniania i sortowania rekordów."""
    return [
        analyze_enzyme(enzyme)
        for enzyme in enzymes
    ]
