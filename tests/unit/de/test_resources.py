"""Unit tests for the Design Ecologique resources module."""

from unittest.mock import Mock, patch

import pytest

from permaculture.de.resources import (
    DesignEcologique,
    main,
)

from ..stubs import StubRequestsResponse


def test_de_resources_perenial_plants():
    """Perenial plants should GET and return the spreadsheet."""
    text = "<a href='https://docs.google.com/spreadsheets/d/test_id/edit'>"
    client = Mock(get=Mock(return_value=StubRequestsResponse(text=text)))
    plants = DesignEcologique(client).perenial_plants()
    client.get.assert_called_once_with("liste-de-plantes-vivaces")
    assert plants.doc_id == "test_id"


def test_de_resources_perenial_plants_error():
    """Perenial plants should raise when spreadhseet is not found."""
    client = Mock(get=Mock(return_value=StubRequestsResponse()))
    with pytest.raises(KeyError):
        DesignEcologique(client).perenial_plants()


@patch("sys.stdout")
def test_main_help(stdout):
    """The main function should output usage when asked for --help."""
    with pytest.raises(SystemExit):
        main(["--help"])

    stdout.write.call_args[0][0].startswith("usage")
