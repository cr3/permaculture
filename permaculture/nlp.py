"""Natural language processing functions."""

import re
import string

from unidecode import unidecode


def normalize(text):
    """Transform text to a more consistent and simplified format."""
    # Strip leading and trailing spaces.
    text = text.strip()

    # Remove parentheses.
    text = re.sub(r"\([^)]*\)", "", text)

    # Remove brackets.
    text = re.sub(r"\[[^]]*\]", "", text)

    # Remove unicode characters.
    text = unidecode(text)

    # Lower case.
    text = text.lower()

    # Remove punctuation.
    text = " ".join(re.findall(r"\w+", text))

    # Remove words smaller than a minimum length.
    text = " ".join(w for w in text.split() if len(w) > 1)

    # Remove digits.
    text = " ".join(w for w in text.split() if w not in string.digits)

    return text
