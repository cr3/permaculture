"""Tokenizer functions."""

import re
from string import digits

from unidecode import unidecode


def tokenize(words):
    # Strip leading and trailing spaces.
    words = words.strip()
    # Remove parentheses.
    words = re.sub(r"\([^)]*\)", "", words)
    # Remove brackets.
    words = re.sub(r"\[[^]]*\]", "", words)
    # Remove accents.
    words = unidecode(words)
    # Remove punctuation.
    words = re.sub(r"[^\w\s]+", " ", words)
    # Remove single letters and spaces.
    words = " ".join(w for w in words.split() if len(w) > 1 or w in digits)
    # Lower case.
    words = words.lower()
    return words
