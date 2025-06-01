import hashlib
import re
from .models import Message


def normalize_number(number: str):
    for char in [
        "(",
        ")",
        "-",
        " ",
        "+",
        "+1",
        ".",
    ]:
        number = number.replace(char, "")

    number = re.sub(r"^1", r"", number)

    return number.strip()
