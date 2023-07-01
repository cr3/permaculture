"""Unit tests for the action module."""

from argparse import ArgumentParser

import pytest
from hamcrest import assert_that, has_properties

from permaculture.action import SingleAction


def test_single_action():
    """A SingleAction should allow a single action."""
    parser = ArgumentParser()
    parser.add_argument("--action", action=SingleAction)

    result = parser.parse_args(["--action", "test"])

    assert_that(result, has_properties(action="test"))


def test_single_action_value_error():
    """A SingleAction with nargs should raise a ValueError."""
    parser = ArgumentParser()

    with pytest.raises(ValueError):
        parser.add_argument("--action", action=SingleAction, nargs=1)
