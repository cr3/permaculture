"""Browser-based fetching with Playwright."""

import logging
from collections.abc import Callable
from contextlib import contextmanager, suppress

from attrs import define, evolve, field

from permaculture.storage import Storage, hash_request, null_storage

logger = logging.getLogger(__name__)


@define(frozen=True)
class BrowserResponse:
    """Adapter that provides a .text attribute from browser page content."""

    text: str


@define(frozen=True)
class BrowserSession:
    """Browser session using a Playwright page."""

    origin: str
    page: object
    storage: Storage = field(default=null_storage)

    def with_cache(self, storage):
        """Return a new session with caching enabled."""
        return evolve(self, storage=storage)

    def get(self, path):
        """Navigate to origin + path and return a ResponseAdapter."""
        url = self.origin + path
        key = hash_request("GET", url)
        with suppress(KeyError):
            return self.storage[key]

        self.page.goto(url)
        response = BrowserResponse(self.page.content())
        try:
            self.storage[key] = response
        except Exception:
            logger.warning("Failed to cache %(url)s", {"url": url})

        return response


@define(frozen=True)
class BrowserClient:
    """Browser client using Playwright."""

    origin: str
    storage: Storage = field(default=null_storage)
    page_factory: Callable | None = field(default=None)

    def with_cache(self, storage):
        return evolve(self, storage=storage)

    @contextmanager
    def open(self):
        """Open a browser session."""
        if self.page_factory:
            yield BrowserSession(self.origin, self.page_factory(), self.storage)
            return

        from playwright.sync_api import sync_playwright

        pw = sync_playwright().start()
        try:
            try:
                browser = pw.chromium.launch()
            except Exception as exc:
                raise RuntimeError(
                    "Browser not found. Run: playwright install chromium"
                ) from exc
            try:
                yield BrowserSession(self.origin, browser.new_page(), self.storage)
            finally:
                browser.close()
        finally:
            pw.stop()

    def get(self, path):
        """Convenience: open a session, fetch, and close."""
        with self.open() as session:
            return session.get(path)
