"""Unit tests for the testing unique module."""

from http.cookiejar import Cookie, CookieJar

import pytest
from hamcrest import assert_that, is_

from permaculture.testing.unique import (
    unique_cookie,
    unique_cookies,
)


@pytest.mark.parametrize(
    "name, matches",
    [
        ("cookie", is_(Cookie)),
        ("cookies", is_(CookieJar)),
    ],
)
def test_unique_types(name, matches, unique):
    """Unique fixtures should return expected types."""
    assert_that(unique(name), matches)


@pytest.mark.parametrize(
    "plugin",
    [
        pytest.param(unique_cookie, id="cookie"),
        pytest.param(unique_cookies, id="cookies"),
    ],
)
def test_unique_plugin_twice(plugin, unique):
    """Calling any plugin twice should not return the same value."""
    assert plugin(unique) != plugin(unique)


@pytest.mark.parametrize(
    "count",
    [
        0,
        1,
        2,
    ],
)
def test_unique_cookies_count(count, unique):
    """Passing a count should return that many cookies."""
    assert len(unique_cookies(unique, count)) == count
