"""Unit tests for the Google module."""

from unittest.mock import Mock

from yarl import URL

from permaculture.google import GoogleSpreadsheet

from .stubs import StubRequestsResponse


def test_google_spreadsheet_from_url(unique):
    """Instantiating from URL should parse the doc ID."""
    doc_id = unique("text")
    url = URL(f"https://docs.google.com/spreadsheets/d/{doc_id}/edit")
    gs = GoogleSpreadsheet.from_url(url)
    assert gs.doc_id == doc_id


def test_google_spreadsheet_export(unique):
    """Exporting should GET with gid and format params."""
    doc_id, gid, fmt = unique("text"), unique("text"), unique("text")
    session = Mock(post=Mock(return_value=StubRequestsResponse()))
    GoogleSpreadsheet(session, doc_id).export(gid, fmt)
    session.get.assert_called_once_with(
        f"/spreadsheets/d/{doc_id}/export",
        params={"gid": gid, "format": fmt},
    )
