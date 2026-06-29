from dataclasses import dataclass


@dataclass
class EnzymeRecord:
    uniprot_id: str
    protein_name: str
    organism: str
    molecular_weight: int
    ec_number: str
    sequence: str

    @property
    def sequence_length(self) -> int:
        return len(self.sequence)