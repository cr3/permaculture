"""Unit tests for the serializer module."""
import pytest

from permaculture.registry import registry_add
from permaculture.serializer import (
    Serializer,
    SerializerNotFound,
    SerializerPlugin,
    octet_stream_serializer,
    text_plain_serializer,
    www_form_serializer,
)

INT_TEST = 0
FLOAT_TEST = 3.1416
BYTES_TEST = b"bytes"
STRING_TEST = "abcdé\u8463"
LIST_TEST = [
    INT_TEST,
    FLOAT_TEST,
    STRING_TEST,
]
DICT_TEST = {
    "int": INT_TEST,
    "float": FLOAT_TEST,
    "string": STRING_TEST,
    "list": LIST_TEST,
}


@pytest.fixture(
    params=[
        "application/json",
        "application/x-pickle",
    ]
)
def serializer(request):
    """Produce pytest parameters for all serializers."""
    return Serializer.load(request.param, {})


def test_init_not_found():
    """Initializing with an unknown content type should raise an exception."""
    content_type = "test"
    with pytest.raises(SerializerNotFound):
        Serializer.load(content_type)


def test_encode_optimized_bytes():
    """Encoding bytes with optimization should return an octet stream."""
    serializer = Serializer.load()
    _, content_type, charset = serializer.encode(BYTES_TEST, optimize=True)
    assert content_type == "application/octet-stream"
    assert charset == "binary"


def test_encode_optimized_string():
    """Encoding a string with optimization should return plain text."""
    serializer = Serializer.load()
    _, content_type, charset = serializer.encode(STRING_TEST, optimize=True)
    assert content_type == "text/plain"
    assert charset == "utf-8"


def test_encode_optimized_other():
    """Encoding other data with optimization should use the default."""
    content_type = "test"
    registry = registry_add(
        "serializers",
        content_type,
        octet_stream_serializer,
    )
    serializer = Serializer.load(content_type, registry)
    assert content_type == serializer.encode(LIST_TEST, optimize=True)[1]


def test_serialize_content_type():
    """Serializing a given content type should override the default."""
    registry = registry_add(
        "serializers",
        "application/octet-stream",
        octet_stream_serializer,
    )
    registry = registry_add(
        "serializers",
        "text/plain",
        text_plain_serializer,
        registry,
    )
    serializer = Serializer.load("text/plain", registry)
    content_type = serializer.encode(
        None, content_type="application/octet-stream"
    )[1]
    assert content_type == "application/octet-stream"
    data = serializer.decode(None, content_type="application/octet-stream")
    assert data is None


def test_serializer_encode_error(serializer):
    """A serializer should raise when encoding an unknown content type."""
    content_type = "test"
    with pytest.raises(SerializerNotFound):
        serializer.encode("", content_type)


def test_serializer_decode_error(serializer):
    """A serializer should raise when decoding an unknown content type."""
    content_type = "test"
    with pytest.raises(SerializerNotFound):
        serializer.decode(b"", content_type)


def test_serializer_exception():
    """A serializer that raises an exception should be re-raised."""

    class TestException(Exception):
        """Test exception."""

    def test_serializer(_):
        """Test serializer raising an exception."""
        raise TestException

    content_type = "test"
    registry = registry_add(
        "serializers",
        content_type,
        SerializerPlugin(test_serializer, test_serializer, "test"),
    )
    serializer = Serializer.load(content_type, registry)
    with pytest.raises(TestException):
        serializer.encode(None)
    with pytest.raises(TestException):
        serializer.decode(None)


def test_octet_stream_serializer():
    """The application/octet-stream content type should not encode a string."""
    payload = octet_stream_serializer.encode(BYTES_TEST)
    assert isinstance(payload, bytes)
    assert octet_stream_serializer.decode(payload) == BYTES_TEST


def test_text_plain_serializer():
    """The text/plain content type should encode a string."""
    payload = text_plain_serializer.encode(STRING_TEST)
    assert isinstance(payload, bytes)
    assert text_plain_serializer.decode(payload) == STRING_TEST


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(
            {},
            id="empty",
        ),
        pytest.param(
            {"key": "value"},
            id="single",
        ),
        pytest.param(
            {"key1": "value1", "key2": "value2"},
            id="multiple",
        ),
    ],
)
def test_www_form_serializer(data):
    """Should serialize and deserialize to the same data."""
    payload = www_form_serializer.encode(data)
    assert isinstance(payload, bytes)
    assert www_form_serializer.decode(payload) == data


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(
            INT_TEST,
            id="int",
        ),
        pytest.param(
            FLOAT_TEST,
            id="float",
        ),
        pytest.param(
            STRING_TEST,
            id="string",
        ),
        pytest.param(
            LIST_TEST,
            id="list",
        ),
        pytest.param(
            DICT_TEST,
            id="dict",
        ),
    ],
)
def test_encode_decode(data, serializer):
    """Encoding data and decoding the returned payload should be the same."""
    payload, _, _ = serializer.encode(data)
    assert isinstance(payload, bytes)
    assert serializer.decode(payload) == data
