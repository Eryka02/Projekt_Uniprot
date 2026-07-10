EC_CLASS_NAMES = {
    "1": "Oksydoreduktaza",
    "2": "Transferaza",
    "3": "Hydrolaza",
    "4": "Liaza",
    "5": "Izomeraza",
    "6": "Ligaza",
    "7": "Translokaza",
}


EC_CLASS_GROUP_LABELS = {
    "1": "1. Oksydoreduktazy",
    "2": "2. Transferazy",
    "3": "3. Hydrolazy",
    "4": "4. Liazy",
    "5": "5. Izomerazy",
    "6": "6. Ligazy",
    "7": "7. Translokazy",
}


def get_ec_class_number(ec_number: str) -> str | None:
    first_ec = str(ec_number or "").split(",")[0].strip()
    first_digit = first_ec[:1]

    if first_digit in EC_CLASS_NAMES:
        return first_digit

    return None


def get_ec_class_name(ec_number: str) -> str:
    class_number = get_ec_class_number(ec_number)

    if class_number:
        return EC_CLASS_NAMES[class_number]

    return "Brak EC"


def get_ec_class_group_label(ec_number: str) -> str:
    class_number = get_ec_class_number(ec_number)

    if class_number:
        return EC_CLASS_GROUP_LABELS[class_number]

    return "Brak EC"
