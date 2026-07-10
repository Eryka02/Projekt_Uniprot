import json
import logging
import re
import time
from pathlib import Path

import requests

from src.uniprot_enzyme_explorer.models import EnzymeRecord


BASE_URL = "https://rest.uniprot.org/uniprotkb"
ENA_FASTA_URL = "https://www.ebi.ac.uk/ena/browser/api/fasta"
NCBI_FASTA_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
REQUEST_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "UniProtEnzymeExplorer/1.0",
}
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_UNIPROT_RETRIES = 3
RETRY_DELAY_SECONDS = 1.0
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
NUCLEOTIDE_DATA_DIR = RAW_DATA_DIR / "nucleotide"
MAX_SUMMARY_LENGTH = 220
STRUCTURE_FEATURES = {
    "Helix": "helisy",
    "Beta strand": "nici beta",
    "Turn": "zakręty",
}
STRUCTURE_METHODS = {
    "X-ray": "krystalografia rentgenowska",
    "NMR": "NMR",
    "EM": "mikroskopia elektronowa / cryo-EM",
    "Electron microscopy": "mikroskopia elektronowa / cryo-EM",
    "Fiber diffraction": "dyfrakcja włókien",
    "Neutron": "dyfrakcja neutronowa",
    "Neutron diffraction": "dyfrakcja neutronowa",
    "Model": "modelowanie",
    "Other": "inna metoda",
}
TERM_TRANSLATIONS = {
    "hydrogen peroxide": "nadtlenek wodoru",
    "carbon dioxide": "dwutlenek węgla",
    "hydrogencarbonate": "jon wodorowęglanowy",
    "bicarbonate": "wodorowęglan",
    "phosphoenolpyruvate": "fosfoenolopirogronian",
    "phosphoglycerate": "fosfoglicerynian",
    "glyceroyl": "glicerylo",
    "glyceraldehyde": "aldehyd glicerynowy",
    "cyanamide": "cyjanamid",
    "pyruvate": "pirogronian",
    "lactate": "mleczan",
    "glucose": "glukoza",
    "fructose": "fruktoza",
    "mannose": "mannoza",
    "hexose": "heksoza",
    "phosphate": "fosforan",
    "phospho": "fosfo",
    "protein": "białko",
    "oxygen": "tlen",
    "water": "woda",
    "urea": "mocznik",
    "alcohol": "alkohol",
    "heme": "hem",
    "magnesium": "magnez",
    "zinc": "cynk",
    "copper": "miedź",
    "iron": "żelazo",
    "metal cation": "kation metalu",
}
SUBCELLULAR_LOCATION_TRANSLATIONS = {
    "Cell membrane": "błona komórkowa",
    "Cell projection": "wypustka komórkowa",
    "Cytoplasm": "cytoplazma",
    "Cytoplasm, cytosol": "cytoplazma, cytozol",
    "Cytoplasmic granule": "ziarnistość cytoplazmatyczna",
    "Cytosol": "cytozol",
    "Endoplasmic reticulum": "siateczka śródplazmatyczna",
    "Extracellular space": "przestrzeń pozakomórkowa",
    "Golgi apparatus": "aparat Golgiego",
    "Lysosome": "lizosom",
    "Membrane": "błona",
    "Mitochondrion": "mitochondrium",
    "Mitochondrion inner membrane": "wewnętrzna błona mitochondrialna",
    "Mitochondrion matrix": "macierz mitochondrialna",
    "Nucleus": "jądro komórkowe",
    "Peroxisome": "peroksysom",
    "Peroxisome matrix": "macierz peroksysomalna",
    "Secreted": "wydzielane poza komórkę",
}


class UniProtError(Exception):
    pass


def raw_data_file(uniprot_id: str) -> Path:
    return RAW_DATA_DIR / f"{uniprot_id.upper()}.json"


def load_raw_uniprot_data(uniprot_id: str) -> dict | None:
    raw_file = raw_data_file(uniprot_id)

    if not raw_file.exists():
        return None

    try:
        with raw_file.open(encoding="utf-8") as file:
            data = json.load(file)
            logging.info("Wczytano dane UniProt z cache: %s", raw_file)
            return data
    except (OSError, json.JSONDecodeError) as error:
        logging.warning("Nie udało się wczytać cache %s: %s", raw_file, error)
        return None


def save_raw_uniprot_data(uniprot_id: str, data: dict):
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    raw_file = raw_data_file(uniprot_id)

    with raw_file.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    logging.info("Zapisano surowe dane UniProt: %s", raw_file)


def _uniprot_http_error_message(status_code: int) -> str:
    if status_code in RETRYABLE_STATUS_CODES:
        return (
            f"UniProt chwilowo zwrócił błąd serwera ({status_code}). "
            "Spróbuj ponownie za chwilę."
        )

    return f"UniProt zwrócił błąd HTTP {status_code}."


def nucleotide_data_file(accession: str) -> Path:
    safe_accession = re.sub(r"[^A-Za-z0-9_.-]", "_", accession)
    return NUCLEOTIDE_DATA_DIR / f"{safe_accession}.fasta"


def load_nucleotide_fasta(accession: str) -> str | None:
    fasta_file = nucleotide_data_file(accession)

    if not fasta_file.exists():
        return None

    try:
        return fasta_file.read_text(encoding="utf-8")
    except OSError as error:
        logging.warning(
            "Nie udało się wczytać cache sekwencji nukleotydowej %s: %s",
            fasta_file,
            error,
        )
        return None


def save_nucleotide_fasta(accession: str, fasta_text: str):
    NUCLEOTIDE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    fasta_file = nucleotide_data_file(accession)
    fasta_file.write_text(fasta_text, encoding="utf-8")
    logging.info("Zapisano sekwencję nukleotydową: %s", fasta_file)


def fetch_uniprot_data(uniprot_id: str) -> dict:
    url = f"{BASE_URL}/{uniprot_id}.json"

    try:
        for attempt in range(1, MAX_UNIPROT_RETRIES + 1):
            response = requests.get(
                url,
                headers=REQUEST_HEADERS,
                timeout=30,
            )

            if response.status_code == 404:
                raise UniProtError(
                    f"Nie znaleziono rekordu UniProt: {uniprot_id}"
                )

            if response.status_code in RETRYABLE_STATUS_CODES:
                logging.warning(
                    "UniProt zwrócił %s dla %s, próba %s/%s.",
                    response.status_code,
                    uniprot_id,
                    attempt,
                    MAX_UNIPROT_RETRIES,
                )
                if attempt < MAX_UNIPROT_RETRIES:
                    time.sleep(RETRY_DELAY_SECONDS * attempt)
                    continue

                raise UniProtError(
                    _uniprot_http_error_message(response.status_code)
                )

            response.raise_for_status()
            data = response.json()
            save_raw_uniprot_data(uniprot_id, data)
            return data

    except requests.Timeout as error:
        raise UniProtError("UniProt nie odpowiedział w wymaganym czasie.") from error

    except requests.RequestException as error:
        response = getattr(error, "response", None)
        if response is not None:
            raise UniProtError(
                _uniprot_http_error_message(response.status_code)
            ) from error

        raise UniProtError("Nie udało się połączyć z UniProt.") from error


def _clean_text(value: str) -> str:
    value = re.sub(r"\s*\(PubMed:[^)]+\)", "", value or "")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _shorten(value: str, max_length: int = MAX_SUMMARY_LENGTH) -> str:
    value = _clean_text(value)

    if not value:
        return "Brak danych"

    if len(value) <= max_length:
        return value

    return value[:max_length].rsplit(" ", 1)[0] + "..."


def _comments_by_type(data: dict, comment_type: str) -> list[dict]:
    return [
        comment
        for comment in data.get("comments", [])
        if comment.get("commentType") == comment_type
    ]


def _text_comment(data: dict, comment_type: str) -> str:
    values = []

    for comment in _comments_by_type(data, comment_type):
        for text in comment.get("texts", []):
            if text.get("value"):
                values.append(text["value"])

    return _shorten(" ".join(values))


def _translate_common_terms(value: str) -> str:
    translated = value

    for english_text, polish_text in sorted(
        TERM_TRANSLATIONS.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        translated = re.sub(
            re.escape(english_text),
            polish_text,
            translated,
            flags=re.IGNORECASE,
        )

    return translated


def _translate_location(value: str) -> str:
    if value in SUBCELLULAR_LOCATION_TRANSLATIONS:
        return SUBCELLULAR_LOCATION_TRANSLATIONS[value]

    translated = value
    for english_text, polish_text in sorted(
        SUBCELLULAR_LOCATION_TRANSLATIONS.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        translated = re.sub(
            re.escape(english_text),
            polish_text,
            translated,
            flags=re.IGNORECASE,
        )

    return _translate_common_terms(translated)


def _polish_function_description(data: dict) -> str:
    text = _text_comment(data, "FUNCTION")

    if text == "Brak danych":
        return text

    lower_text = text.lower()
    templates = [
        (
            "reversible hydration of carbon dioxide",
            "Katalizuje odwracalną hydratację dwutlenku węgla.",
        ),
        (
            "hydrogen peroxide",
            "Rozkłada nadtlenek wodoru do wody i tlenu, chroniąc komórkę przed stresem oksydacyjnym.",
        ),
        (
            "glycolysis",
            "Uczestniczy w przemianach glikolizy, czyli szlaku pozyskiwania energii z cukrów.",
        ),
        (
            "glycolytic pathway",
            "Uczestniczy w przemianach glikolizy, czyli szlaku pozyskiwania energii z cukrów.",
        ),
        (
            "phosphorylation of hexose",
            "Fosforyluje heksozy, np. glukozę, przygotowując je do dalszych etapów metabolizmu.",
        ),
        (
            "nitric oxide",
            "Wytwarza tlenek azotu (NO), cząsteczkę ważną w przekazywaniu sygnałów w organizmie.",
        ),
        (
            "cytochrome p450 monooxygenase",
            "Działa jako monooksygenaza cytochromu P450 i uczestniczy w metabolizmie związków organicznych.",
        ),
        (
            "serine protease",
            "Działa jako proteaza serynowa, czyli enzym rozcinający wybrane wiązania w białkach.",
        ),
        (
            "metalloproteinase",
            "Działa jako metaloproteinaza, czyli enzym rozkładający wybrane białka z udziałem jonu metalu.",
        ),
        (
            "peroxidase",
            "Działa jako peroksydaza i bierze udział w reakcjach związanych z nadtlenkami.",
        ),
        (
            "destroys radicals",
            "Neutralizuje rodniki powstające w komórce i ogranicza ich toksyczne działanie.",
        ),
        (
            "interconverts",
            "Wzajemnie przekształca substraty i produkty swojej reakcji enzymatycznej.",
        ),
        (
            "regulatory subunit",
            "Pełni funkcję podjednostki regulatorowej i wpływa na swoistość działania kompleksu enzymatycznego.",
        ),
    ]

    for marker, summary in templates:
        if marker in lower_text:
            return summary

    if _catalytic_activity(data) != "Brak danych":
        return (
            "Katalizuje reakcję enzymatyczną; szczegółowe równanie "
            "jest podane niżej."
        )

    return (
        "UniProt zawiera opis funkcji tego białka, ale aplikacja nie ma "
        "gotowego polskiego skrótu dla tego typu opisu."
    )

def _catalytic_activity(data: dict) -> str:
    reactions = []

    for comment in _comments_by_type(data, "CATALYTIC ACTIVITY"):
        reaction = comment.get("reaction", {})
        name = reaction.get("name")
        if name:
            reactions.append(name)

    if not reactions:
        return "Brak danych"

    return _translate_common_terms("; ".join(reactions[:2]))


def _cofactors(data: dict) -> str:
    names = []

    for comment in _comments_by_type(data, "COFACTOR"):
        for cofactor in comment.get("cofactors", []):
            name = cofactor.get("name")
            if name and name not in names:
                names.append(name)

    if not names:
        return "Brak danych"

    return _translate_common_terms(", ".join(names))


def _subcellular_location(data: dict) -> str:
    locations = []

    for comment in _comments_by_type(data, "SUBCELLULAR LOCATION"):
        for item in comment.get("subcellularLocations", []):
            location = item.get("location", {}).get("value")
            if location:
                translated_location = _translate_location(location)
                if translated_location not in locations:
                    locations.append(translated_location)

    return ", ".join(locations) or "Brak danych"


def _feature_summary(data: dict) -> str:
    feature_names = {
        "Active site": "aktywne miejsca",
        "Binding site": "miejsca wiązania",
        "Domain": "domeny",
        "Motif": "motywy",
    }
    counts = {
        label: 0
        for label in feature_names.values()
    }

    for feature in data.get("features", []):
        label = feature_names.get(feature.get("type"))
        if label:
            counts[label] += 1

    parts = [
        f"{label}: {count}"
        for label, count in counts.items()
        if count
    ]

    return "; ".join(parts) or "Brak danych"


def _reference_properties(reference: dict) -> dict[str, str]:
    return {
        item.get("key"): item.get("value")
        for item in reference.get("properties", [])
        if item.get("key") and item.get("value")
    }


def _reference_property(reference: dict, key: str) -> str:
    return _reference_properties(reference).get(key, "")


def _select_nucleotide_reference(data: dict) -> dict | None:
    candidates = []

    for reference in data.get("uniProtKBCrossReferences", []):
        database = reference.get("database")

        if database == "EMBL":
            accession = reference.get("id")
            if not accession:
                continue

            molecule_type = _reference_property(reference, "MoleculeType")
            status = _reference_property(reference, "Status")
            molecule_rank = {
                "mRNA": 0,
                "cDNA": 1,
                "Genomic_DNA": 3,
            }.get(molecule_type, 2)
            status_rank = {
                "-": 0,
                "JOINED": 2,
            }.get(status, 1)

            candidates.append(
                {
                    "accession": accession,
                    "database": "EMBL/ENA",
                    "fetcher": "ENA",
                    "molecule_type": molecule_type or "sekwencja nukleotydowa",
                    "rank": (molecule_rank, status_rank),
                }
            )

        elif database == "RefSeq":
            accession = _reference_property(reference, "NucleotideSequenceId")
            if accession:
                candidates.append(
                    {
                        "accession": accession,
                        "database": "RefSeq",
                        "fetcher": "NCBI",
                        "molecule_type": "mRNA / RefSeq",
                        "rank": (1, 0),
                    }
                )

    if not candidates:
        return None

    return sorted(candidates, key=lambda item: item["rank"])[0]


def _parse_fasta_sequence(fasta_text: str) -> str:
    lines = [
        line.strip()
        for line in fasta_text.splitlines()
        if line.strip() and not line.startswith(">")
    ]
    sequence = "".join(lines).upper()
    return re.sub(r"[^ACGTUNRYKMSWBDHV]", "", sequence)


def _download_nucleotide_fasta(reference: dict) -> str:
    accession = reference["accession"]

    if reference["fetcher"] == "NCBI":
        response = requests.get(
            NCBI_FASTA_URL,
            params={
                "db": "nuccore",
                "id": accession,
                "rettype": "fasta",
                "retmode": "text",
            },
            timeout=8,
        )
    else:
        response = requests.get(
            f"{ENA_FASTA_URL}/{accession}",
            params={"download": "false"},
            timeout=8,
        )

    response.raise_for_status()
    return response.text


def _nucleotide_sequence(data: dict) -> tuple[str, str]:
    reference = _select_nucleotide_reference(data)

    if reference is None:
        return "", "Brak odnośnika nukleotydowego w rekordzie UniProt"

    accession = reference["accession"]
    source = (
        f"{reference['database']} {accession} "
        f"({reference['molecule_type']})"
    )
    fasta_text = load_nucleotide_fasta(accession)

    try:
        if fasta_text is None:
            fasta_text = _download_nucleotide_fasta(reference)
            save_nucleotide_fasta(accession, fasta_text)

        sequence = _parse_fasta_sequence(fasta_text)
        if sequence:
            return sequence, source

        return "", f"{source} - brak sekwencji w pobranym pliku FASTA"

    except requests.RequestException as error:
        logging.warning(
            "Nie udało się pobrać sekwencji nukleotydowej %s: %s",
            accession,
            error,
        )
        return "", f"{source} - nie udało się pobrać sekwencji"

    except OSError as error:
        logging.warning(
            "Nie udało się zapisać sekwencji nukleotydowej %s: %s",
            accession,
            error,
        )
        return "", f"{source} - nie udało się zapisać cache"


def _best_resolution(pdb_references: list[dict]) -> str | None:
    best_value = None
    best_label = None

    for reference in pdb_references:
        resolution = _reference_properties(reference).get("Resolution")
        if not resolution or resolution == "-":
            continue

        match = re.search(r"\d+(?:\.\d+)?", resolution)
        if not match:
            continue

        value = float(match.group())
        if best_value is None or value < best_value:
            best_value = value
            best_label = resolution.replace("A", "Å")

    return best_label


def _structure_summary(data: dict) -> str:
    references = data.get("uniProtKBCrossReferences", [])
    pdb_references = [
        reference
        for reference in references
        if reference.get("database") == "PDB"
    ]
    alphafold_references = [
        reference
        for reference in references
        if reference.get("database") == "AlphaFoldDB"
    ]

    parts = []

    if pdb_references:
        methods = []

        for reference in pdb_references:
            method = _reference_properties(reference).get("Method")
            if not method:
                continue

            method = STRUCTURE_METHODS.get(method, method)
            if method not in methods:
                methods.append(method)

        method_text = ", ".join(methods[:3]) if methods else "brak opisu metody"
        parts.append(
            f"struktura 3D eksperymentalna w PDB "
            f"({len(pdb_references)} wpisów; metoda: {method_text})"
        )

        best_resolution = _best_resolution(pdb_references)
        if best_resolution:
            parts.append(f"najlepsza rozdzielczość: {best_resolution}")

    if alphafold_references:
        parts.append("model 3D predykcyjny AlphaFold")

    secondary_counts = {
        label: 0
        for label in STRUCTURE_FEATURES.values()
    }
    for feature in data.get("features", []):
        label = STRUCTURE_FEATURES.get(feature.get("type"))
        if label:
            secondary_counts[label] += 1

    secondary_parts = [
        f"{label}: {count}"
        for label, count in secondary_counts.items()
        if count
    ]
    if secondary_parts:
        parts.append(
            "struktura drugorzędowa/2D: " + ", ".join(secondary_parts)
        )

    return "; ".join(parts) or "Brak danych o strukturze w UniProt"


def build_enzyme_record(data: dict) -> EnzymeRecord:
    entry_type = data.get("entryType", "").lower()

    if "unreviewed" in entry_type:
        reviewed_status = "unreviewed"
    elif "reviewed" in entry_type:
        reviewed_status = "reviewed"
    else:
        reviewed_status = "Brak danych"

    protein_description = data["proteinDescription"]
    recommended_name = protein_description["recommendedName"]
    protein_name = recommended_name["fullName"]["value"]

    ec_numbers = recommended_name.get("ecNumbers", [])
    ec_number = ", ".join(
        item["value"] for item in ec_numbers
    ) or "Brak"

    sequence_data = data["sequence"]
    nucleotide_sequence, nucleotide_source = _nucleotide_sequence(data)

    return EnzymeRecord(
        uniprot_id=data["primaryAccession"],
        protein_name=protein_name,
        organism=data["organism"]["scientificName"],
        molecular_weight=sequence_data["molWeight"],
        ec_number=ec_number,
        sequence=sequence_data["value"],
        nucleotide_sequence=nucleotide_sequence,
        nucleotide_source=nucleotide_source,
        reviewed_status=reviewed_status,
        function_description=_polish_function_description(data),
        catalytic_activity=_catalytic_activity(data),
        cofactors=_cofactors(data),
        subcellular_location=_subcellular_location(data),
        feature_summary=_feature_summary(data),
        structure_summary=_structure_summary(data),
    )


def fetch_enzyme(uniprot_id: str) -> EnzymeRecord:
    data = load_raw_uniprot_data(uniprot_id)

    if data is None:
        logging.info("Pobieranie danych UniProt z internetu: %s", uniprot_id)
        data = fetch_uniprot_data(uniprot_id)

    try:
        return build_enzyme_record(data)
    except KeyError as error:
        raise UniProtError(
            f"Rekord UniProt ma nieoczekiwany format: {error}"
        ) from error
