from dataclasses import dataclass


@dataclass
class EnzymeRecord:
    uniprot_id: str
    protein_name: str
    organism: str
    molecular_weight: int
    ec_number: str
    sequence: str
    reviewed_status: str = "Brak danych"
    quality_score: int = 0
    hydrophobic_count: int = 0
    hydrophobic_percent: float = 0.0
    cysteine_count: int = 0
    cysteine_percent: float = 0.0
    most_common_amino_acid: str = "Brak"
    sequence_length_category: str = "Brak"
    interpretation: str = ""

    @property
    def sequence_length(self):
        return len(self.sequence)