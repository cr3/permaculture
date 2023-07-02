"""Unit tests for the action module."""

from argparse import ArgumentParser
from enum import Enum

import pytest
from hamcrest import assert_that, has_properties

from permaculture.action import EnumAction, SingleAction

StubEnum = Enum("StubEnum", ["a", "b"])


def test_enum_action():
    """An EnumAction should return an enum instance."""
    parser = ArgumentParser()
    parser.add_argument("--enum", action=EnumAction, type=StubEnum)

    result = parser.parse_args(["--enum", "a"])

    assert_that(result, has_properties(enum=StubEnum.a))


def test_enum_action_default():
    """An EnumAction should return the default when specified."""
    parser = ArgumentParser()
    parser.add_argument(
        "--enum",
        action=EnumAction,
        type=StubEnum,
        default=StubEnum.a,
    )

    result = parser.parse_args([])

    assert_that(result, has_properties(enum=StubEnum.a))


def test_enum_action_list():
    """An EnumAction should return a list of values."""
    parser = ArgumentParser()
    parser.add_argument(
        "--enum",
        action=EnumAction,
        type=StubEnum,
        nargs="*",
    )

    result = parser.parse_args(["--enum", "a", "b"])

    assert_that(result, has_properties(enum=[StubEnum.a, StubEnum.b]))


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
