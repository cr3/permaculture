"""Natural language processing functions."""

import re
import string
from argparse import ArgumentTypeError

from attrs import define, field
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


def score(s1, s2, sort=True):
    """Calculates the normalized Levenshtein distance between two strings.

    https://en.wikipedia.org/wiki/Levenshtein_distance
    """
    if sort:
        s1 = " ".join(sorted(s1.split()))
        s2 = " ".join(sorted(s2.split()))

    l1, l2 = len(s1), len(s2)
    matrix = [*range(l1 + 1)] * (l2 + 1)
    for zz in range(l2 + 1):
        matrix[zz] = [*range(zz, zz + l1 + 1)]

    for zz in range(l2):
        for sz in range(l1):
            if s1[sz] == s2[zz]:
                matrix[zz + 1][sz + 1] = min(
                    matrix[zz + 1][sz] + 1,
                    matrix[zz][sz + 1] + 1,
                    matrix[zz][sz],
                )
            else:
                matrix[zz + 1][sz + 1] = min(
                    matrix[zz + 1][sz] + 1,
                    matrix[zz][sz + 1] + 1,
                    matrix[zz][sz] + 1,
                )

    distance = float(matrix[l2][l1])
    return 1.0 - distance / max(l1, l2)


def score_type(x):
    """Argument parser score type."""
    try:
        x = float(x)
    except ValueError as e:
        raise ArgumentTypeError(f"{x} not a floating-point literal") from e

    if x < 0.0 or x > 1.0:
        raise ArgumentTypeError(f"{x} not in range [0.0, 1.0]")

    return x


@define(frozen=True)
class Extractor:
    query = field()
    normalizer = field(default=lambda x: x)
    scorer = field(default=lambda *_: 1)

    @property
    def normalized_query(self):
        return self.normalizer(self.query)

    def extract(self, choices):
        """Extract the score for each choice."""
        normalized_query = self.normalized_query
        for choice in choices:
            normalized_choice = self.normalizer(choice)
            score = self.scorer(normalized_query, normalized_choice)
            yield (score, choice)

    def extract_one(self, choices):
        """Extract the beschoice with the best score.

        :raises ValueError: When there are no choices.
        """
        results = self.extract(choices)
        return max(results, key=lambda i: i[0])

    def choose(self, choices, default=None):
        result = self.extract_one(choices)
        return result[1] if result else default
