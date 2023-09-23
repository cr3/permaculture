"""Unique plugins."""

from http.cookiejar import Cookie, CookieJar

from permaculture.database import DatabasePlant
from permaculture.tokenizer import tokenize


def unique_cookie(unique):
    """Generate a unique cookie."""
    version = unique("integer")
    name = unique("text")
    value = unique("text")
    port = None
    port_specified = False
    domain = unique("text")
    domain_specified = False
    domain_initial_dot = False
    path = unique("text")
    path_specified = True
    secure = True
    expires = unique("integer")
    discard = False
    comment = None
    comment_url = None
    rest = {"HttpOnly": None}
    rfc2109 = False
    return Cookie(
        version=version,
        name=name,
        value=value,
        port=port,
        port_specified=port_specified,
        domain=domain,
        domain_specified=domain_specified,
        domain_initial_dot=domain_initial_dot,
        path=path,
        path_specified=path_specified,
        secure=secure,
        expires=expires,
        discard=discard,
        comment=comment,
        comment_url=comment_url,
        rest=rest,
        rfc2109=rfc2109,
    )


def unique_cookies(unique, count=1):
    """Generate a cookie jar with unique cookies."""
    cookie_jar = CookieJar()
    for _ in range(count):
        cookie = unique("cookie")
        cookie_jar.set_cookie(cookie)

    return cookie_jar


def unique_plant(unique):
    """Generate a unique database plant."""
    return DatabasePlant(
        {
            "scientific name": unique("token"),
            "common name": unique("text"),
        }
    )


def unique_token(unique):
    """Generate a unique token."""
    return tokenize(unique("text"))
