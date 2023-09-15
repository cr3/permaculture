"""Unit testing fixtures."""

from pytest_unique.fixtures import unique_in_memory

# Use in-memory counter to be faster.
unique = unique_in_memory
