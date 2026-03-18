"""Unit testing fixtures."""

import pytest
from pytest_unique.fixtures import unique_in_memory

from permaculture.database import Database

# Use in-memory counter to be faster.
unique = unique_in_memory


@pytest.fixture
def database():
    """Create an empty in-memory database."""
    db = Database.from_url(":memory:")
    db.initialize()
    return db
