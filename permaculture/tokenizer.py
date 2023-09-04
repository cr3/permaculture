"""Tokenizer functions."""

from unidecode import unidecode


def tokenize(words):
    # Strip leading and trailing spaces.
    words = words.strip()
    # Remove accents.
    words = unidecode(words)
    # Remove single letter words.
    words = " ".join(w for w in words.split() if len(w) > 1)
    # Lower case.
    words = words.lower()
    return words
