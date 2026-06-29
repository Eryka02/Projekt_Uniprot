import requests

from src.uniprot_enzyme_explorer.models import EnzymeRecord


BASE_URL = "https://rest.uniprot.org/uniprotkb"


class UniProtError(Exception):
    pass


def fetch_enzyme(uniprot_id: str) -> EnzymeRecord:
    url = f"{BASE_URL}/{uniprot_id}.json"

    try:
        response = requests.get(url, timeout=30)

        if response.status_code == 404:
            raise UniProtError(
                f"Nie znaleziono rekordu UniProt: {uniprot_id}"
            )

        response.raise_for_status()
        data = response.json()

    except requests.Timeout as error:
        raise UniProtError("UniProt nie odpowiedział w wymaganym czasie.") from error

    except requests.RequestException as error:
        raise UniProtError(f"Błąd połączenia z UniProt: {error}") from error

    protein_description = data["proteinDescription"]
    recommended_name = protein_description["recommendedName"]

    protein_name = recommended_name["fullName"]["value"]

    ec_numbers = recommended_name.get("ecNumbers", [])
    ec_number = ", ".join(
        item["value"] for item in ec_numbers
    ) or "Brak"

    sequence_data = data["sequence"]

    return EnzymeRecord(
        uniprot_id=data["primaryAccession"],
        protein_name=protein_name,
        organism=data["organism"]["scientificName"],
        molecular_weight=sequence_data["molWeight"],
        ec_number=ec_number,
        sequence=sequence_data["value"],
    )