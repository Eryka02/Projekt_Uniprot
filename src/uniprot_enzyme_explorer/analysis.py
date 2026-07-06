from collections import Counter


HYDROPHOBIC_AMINO_ACIDS = set("AILMFWVPG")


def has_value(value) -> bool:
    return value not in (None, "", "Brak", "Brak danych")


def calculate_completeness_score(enzyme) -> int:
    score = 0

    if enzyme.reviewed_status == "reviewed":
        score += 2

    if has_value(enzyme.ec_number):
        score += 2

    if has_value(enzyme.sequence):
        score += 2

    if enzyme.molecular_weight:
        score += 1

    if has_value(enzyme.organism):
        score += 1

    if has_value(enzyme.protein_name):
        score += 1

    has_basic_data = all(
        [
            has_value(enzyme.uniprot_id),
            has_value(enzyme.protein_name),
            has_value(enzyme.organism),
            has_value(enzyme.sequence),
            enzyme.molecular_weight,
        ]
    )

    if has_basic_data:
        score += 1

    return score


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

    parts.append(
        f"uzyskał wynik jakości {enzyme.quality_score}/10"
    )

    if enzyme.quality_score >= 8:
        recommendation = (
            "Może być bardzo dobrym kandydatem do dalszej analizy."
        )
    elif enzyme.quality_score >= 5:
        recommendation = (
            "Może być użyteczny, ale warto sprawdzić braki w adnotacji."
        )
    else:
        recommendation = (
            "Wymaga ostrożności, ponieważ rekord ma niską kompletność danych."
        )

    return ", ".join(parts) + ". " + recommendation


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

    enzyme.quality_score = calculate_completeness_score(enzyme)
    enzyme.interpretation = generate_interpretation(enzyme)

    return enzyme


def rank_enzymes(enzymes):
    analyzed_enzymes = [
        analyze_enzyme(enzyme)
        for enzyme in enzymes
    ]

    return sorted(
        analyzed_enzymes,
        key=lambda enzyme: (
            enzyme.quality_score,
            has_value(enzyme.ec_number),
            enzyme.reviewed_status == "reviewed",
            has_value(enzyme.sequence),
        ),
        reverse=True,
    )