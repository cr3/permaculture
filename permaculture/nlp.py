"""Natural language processing functions."""

import re
from string import digits

from unidecode import unidecode


def normalize(text):
    """Transform text to a more consistent and simplified format."""
    # Strip leading and trailing spaces.
    text = text.strip()
    # Remove parentheses.
    text = re.sub(r"\([^)]*\)", "", text)
    # Remove brackets.
    text = re.sub(r"\[[^]]*\]", "", text)
    # Remove accents.
    text = unidecode(text)
    # Lower case.
    text = text.lower()
    # Remove punctuation.
    words = re.findall(r"\w+", text)
    # Remove single letters and spaces.
    words = [w for w in words if len(w) > 1 or w in digits]
    return " ".join(words)
