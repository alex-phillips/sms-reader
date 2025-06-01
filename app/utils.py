import hashlib
import re
from .models import Message


def compute_message_hash(message: Message) -> str:
    h = hashlib.sha256()
    h.update(str(message.contact_id).encode("utf-8"))
    h.update(str(message.date).encode("utf-8"))
    h.update(message.body.encode("utf-8"))
    h.update(str(message.type).encode("utf-8"))
    return h.hexdigest()


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
