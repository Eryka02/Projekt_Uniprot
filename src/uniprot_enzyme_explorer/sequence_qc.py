from collections import Counter, defaultdict


def find_duplicate_ids(uniprot_ids: list[str]) -> dict[str, int]:
    counts = Counter(identifier.strip().upper() for identifier in uniprot_ids)
    return {
        identifier: count
        for identifier, count in counts.items()
        if identifier and count > 1
    }


def normalize_sequence(sequence: str) -> str:
    return "".join((sequence or "").split()).upper()


def select_representative(records):
    return next(
        (
            record
            for record in records
            if str(record.reviewed_status).lower() == "reviewed"
        ),
        records[0],
    )


def group_identical_sequences(enzymes) -> dict[str, list]:
    sequences = defaultdict(list)
    for enzyme in enzymes:
        enzyme.sequence = normalize_sequence(enzyme.sequence)
        enzyme.qc_status = "Unikalna"
        enzyme.duplicate_group = None
        enzyme.is_representative = True
        enzyme.representative_id = enzyme.uniprot_id
        if enzyme.sequence:
            sequences[enzyme.sequence].append(enzyme)

    groups = {}
    group_number = 1
    for records in sequences.values():
        if len(records) < 2:
            continue

        group_id = f"DUP-{group_number:03d}"
        representative = select_representative(records)
        groups[group_id] = records

        for record in records:
            record.duplicate_group = group_id
            record.representative_id = representative.uniprot_id
            record.is_representative = record is representative
            record.qc_status = (
                "Reprezentant"
                if record.is_representative
                else "Duplikat"
            )

        group_number += 1

    return groups


def prepare_non_redundant_set(enzymes) -> list:
    return [
        enzyme
        for enzyme in enzymes
        if enzyme.sequence and enzyme.is_representative
    ]
