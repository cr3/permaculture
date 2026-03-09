"""Google spreadsheets web interface."""

import re
from pathlib import Path

from attrs import define
from yarl import URL

from permaculture.http import HTTPSession
from permaculture.storage import null_storage


@define(frozen=True)
class GoogleSpreadsheet:
    """Google spreadsheet."""

    session: HTTPSession
    doc_id: str

    @classmethod
    def from_url(cls, url: URL, storage=null_storage):
        session = HTTPSession(url.origin()).with_cache(storage)
        doc_id = Path(url.path).parent.name
        return cls(session, doc_id)

    def sheets(self):
        """List sheets in the spreadsheet."""
        response = self.session.get(
            f"/spreadsheets/d/{self.doc_id}/htmlview",
        )
        return {
            m.group("name"): int(m.group("gid"))
            for m in re.finditer(
                r'items\.push\(\{name:\s*"(?P<name>[^"]*)".*?'
                r'gid:\s*"(?P<gid>\d+)"',
                response.text,
            )
        }

    def export(self, gid=1, fmt="csv"):
        response = self.session.get(
            f"/spreadsheets/d/{self.doc_id}/export",
            params={
                "gid": gid,
                "format": fmt,
            },
        )

        return response.content.decode("utf8")
