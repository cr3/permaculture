"""Google spreadsheets web interface."""

from pathlib import Path

from attrs import define
from requests import Session
from yarl import URL

from permaculture.http import HTTPSession


@define(frozen=True)
class GoogleSpreadsheet:
    """Google spreadsheet."""

    session: Session
    doc_id: str

    @classmethod
    def from_url(cls, url: URL, cache_dir=None):
        session = HTTPSession(url.origin()).with_cache(cache_dir)
        doc_id = Path(url.path).parent.name
        return cls(session, doc_id)

    def export(self, gid=1, fmt="csv"):
        response = self.session.get(
            f"/spreadsheets/d/{self.doc_id}/export",
            params={
                "gid": gid,
                "format": fmt,
            },
        )

        return response.content.decode("utf8")
