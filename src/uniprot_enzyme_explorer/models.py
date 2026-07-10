from dataclasses import dataclass


@dataclass
class EnzymeRecord:
    uniprot_id: str
    protein_name: str
    organism: str
    molecular_weight: int
    ec_number: str
    sequence: str
    nucleotide_sequence: str = ""
    nucleotide_source: str = "Brak danych"
    reviewed_status: str = "Brak danych"
    hydrophobic_count: int = 0
    hydrophobic_percent: float = 0.0
    cysteine_count: int = 0
    cysteine_percent: float = 0.0
    most_common_amino_acid: str = "Brak"
    sequence_length_category: str = "Brak"
    interpretation: str = ""
    qc_status: str = "Unikalna"
    duplicate_group: str | None = None
    is_representative: bool = True
    representative_id: str | None = None
    function_description: str = "Brak danych"
    catalytic_activity: str = "Brak danych"
    cofactors: str = "Brak danych"
    subcellular_location: str = "Brak danych"
    feature_summary: str = "Brak danych"
    structure_summary: str = "Brak danych"

    @property
    def sequence_length(self):
        return len(self.sequence)
