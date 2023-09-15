"""Unit testing stubs."""

from collections.abc import Callable
from http.cookiejar import CookieJar

from attrs import Factory, define, field


@define(frozen=True)
class StubRequestsPreparedRequest:
    """Stub Requests PreparedRequest object."""

    method: str = "GET"
    headers: dict = {}
    body: str = ""
    url: str = "http://www.test.com/"

    def prepare_cookies(self, _):
        """Do nothing."""


@define(frozen=True)
class StubRequestsResponse:
    """Stub Requests Response object."""

    status_code: int = 200
    headers: dict = {}
    json: Callable[[], dict] = lambda: {}
    url: str = "http://www.test.com/"
    reason: str = ""
    text: str = ""
    cookies: CookieJar = None
    request: StubRequestsPreparedRequest = field(
        default=Factory(
            lambda self: StubRequestsPreparedRequest(url=self.url),
            takes_self=True,
        )
    )
