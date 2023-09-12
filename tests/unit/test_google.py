"""Unit tests for the Google module."""

from unittest.mock import Mock

from yarl import URL

from permaculture.google import GoogleSpreadsheet

from .stubs import StubRequestsResponse


def test_google_spreadsheet_from_url():
    """Instantiating from URL should parse the doc ID."""
    url = URL("https://docs.google.com/spreadsheets/d/test_id/edit")
    gs = GoogleSpreadsheet.from_url(url)
    assert gs.doc_id == "test_id"


def test_google_spreadsheet_export():
    """Exporting should GET with gid and format params."""
    client = Mock(post=Mock(return_value=StubRequestsResponse()))
    GoogleSpreadsheet(client, "test_id").export("test_gid", "test_format")
    client.get.assert_called_once_with(
        "/spreadsheets/d/test_id/export",
        params={"gid": "test_gid", "format": "test_format"},
        allow_redirects=False,
    )
