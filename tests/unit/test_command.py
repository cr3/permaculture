"""Unit tests for the command module."""

from unittest.mock import patch

import pytest

from permaculture.command import main


@patch("sys.stdout")
def test_main_help(stdout):
    """The main function should output usage when asked for --help."""
    with pytest.raises(SystemExit):
        main(["--help"])
