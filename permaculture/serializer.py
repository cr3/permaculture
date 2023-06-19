"""Serializers for web related formats."""
import json
import pickle
from typing import Any, Callable
from urllib.parse import parse_qsl, urlencode

from attrs import define

from permaculture.registry import registry_load


class SerializerNotFound(Exception):
    """Raised when a serializer is not found for a content type."""


class Serializer:
    """A serializer to encode and decode data.

    :param content_type: Default content type of the serializer, defaults to
        application/json.
    :param registry: Registry of serializers, defaults to the global registry.
    :raises SerializerNotFound: If the serializer is not found for the content
        type.

    >>> serializer = Serializer()
    >>> serializer.encode('foo') == (b'"foo"', 'application/json', 'utf-8')
    True
    >>> serializer.decode(b'{"key": "value"}') == {'key': 'value'}
    True
    """

    def __init__(self, content_type="application/json", registry=None):
        """Init."""
        if registry is None or "serializers" not in registry:
            registry = registry_load("serializers", registry)

        self._serializers = registry.get("serializers", {})
        self.default_content_type = content_type

    def __repr__(self):
        cls = self.__class__.__name__
        content_type = self.default_content_type
        return f"{cls}(content_type={content_type!r})"

    def _set_default_content_type(self, content_type):
        if content_type not in self._serializers:
            raise SerializerNotFound(f"Serializer {content_type!r} not found")

        self._default_content_type = content_type

    def _get_default_content_type(self):
        return getattr(self, "_default_content_type", None)

    # Default content type used when encoding and decoding data.
    default_content_type = property(
        _get_default_content_type, _set_default_content_type
    )

    def encode(self, data, content_type=None, optimize=False):
        """Encode data based on a content type.

        :param content_type: Content type to override the default value.
        :param optimize: Optimize the content type for string types.
        :return: The encoded payload, content type and charset.
        :raises SerializerNotFound: If the serializer is not found for the
            content type.
        """
        if optimize:
            if isinstance(data, bytes):
                content_type = "application/octet-stream"
            elif isinstance(data, str):
                content_type = "text/plain"

        if content_type is None:
            content_type = self.default_content_type

        try:
            serializer = self._serializers[content_type]
        except KeyError as error:
            raise SerializerNotFound(
                f"Serializer {content_type!r} not found"
            ) from error

        payload = serializer.encode(data)

        return payload, content_type, serializer.charset

    def decode(self, payload, content_type=None):
        """Decode a payload based on a content type.

        :param content_type: Content type to override the default value.
        :param charset: Character set of the payload.
        :return: The decoded data.
        :raises SerializerNotFound: If the serializer is not found for the
            content type or for the expected charset.
        """
        if content_type is None:
            content_type = self.default_content_type

        try:
            serializer = self._serializers[content_type]
        except KeyError as error:
            raise SerializerNotFound(
                f"Serializer {content_type!r} not found"
            ) from error

        return serializer.decode(payload)


@define(frozen=True)
class SerializerPlugin:
    """Serializer with an encode/decode method definable inline."""

    encode: Callable[[Any], bytes]
    decode: Callable[[bytes], Any]
    charset: str


json_serializer = SerializerPlugin(
    lambda data: json.dumps(data).encode("utf-8"),
    lambda payload: json.loads(payload.decode("utf-8")),
    "utf-8",
)
"""Serializer for application/json."""


pickle_serializer = SerializerPlugin(
    pickle.dumps,
    pickle.loads,
    "binary",
)
"""Serializer for application/x-pickle."""


octet_stream_serializer = SerializerPlugin(
    lambda data: data,
    lambda payload: payload,
    "binary",
)
"""Serializer for application/octet-stream.

This serializer doesn't do anything.
"""

text_html_serializer = SerializerPlugin(
    lambda data: data.encode("utf-8"),
    lambda payload: payload.decode("utf-8"),
    "utf-8",
)
"""Serializer for text/html."""

text_plain_serializer = text_html_serializer
"""Serializer for text/plain."""

www_form_serializer = SerializerPlugin(
    lambda data: urlencode(data).encode("utf-8"),
    lambda payload: dict(parse_qsl(payload.decode("utf-8").strip())),
    "utf-8",
)
"""Serializer for application/x-www-form-urlencoded."""
