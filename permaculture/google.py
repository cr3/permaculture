"""Google spreadsheets web interface."""

from pathlib import Path

from attrs import define
from yarl import URL

from permaculture.http import HTTPClient


@define(frozen=True)
class GoogleSpreadsheet:
    """Google spreadsheet."""

    client: HTTPClient
    doc_id: str

    @classmethod
    def from_url(cls, url: URL, cache_dir=None):
        client = HTTPClient.with_cache_all(url.origin(), cache_dir)
        doc_id = Path(url.path).parent.name
        return cls(client, doc_id)

    def export(self, gid=1, fmt="csv"):
        response = self.client.get(
            f"/spreadsheets/d/{self.doc_id}/export",
            params={"gid": gid, "format": fmt},
        )
        return response.content.decode("utf8")
