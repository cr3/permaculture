"""Unit tests for the runner module."""

from unittest.mock import Mock

import pytest

from permaculture.database import DatabasePlant
from permaculture.runner import Runner
from permaculture.sink import SQLiteSink


@pytest.fixture
def sink(tmp_path):
    """Create a SQLiteSink backed by a temporary database."""
    s = SQLiteSink(tmp_path / "test.db")
    s.initialize()
    return s


def test_runner_ingest_single_source(sink):
    """Running with a single source should write all records."""
    records = [
        DatabasePlant({"scientific name": "symphytum officinale"}),
        DatabasePlant({"scientific name": "achillea millefolium"}),
    ]
    source = Mock(fetch_all=Mock(return_value=iter(records)))
    runner = Runner(sources={"test": source}, sink=sink)
    runner.run()

    result = sink.read_all()
    assert len(result) == 2


def test_runner_ingest_multiple_sources(sink):
    """Running with multiple sources should write all records."""
    source_a = Mock(
        fetch_all=Mock(
            return_value=iter(
                [
                    DatabasePlant({"scientific name": "a"}),
                ]
            )
        )
    )
    source_b = Mock(
        fetch_all=Mock(
            return_value=iter(
                [
                    DatabasePlant({"scientific name": "b"}),
                ]
            )
        )
    )
    runner = Runner(
        sources={"a": source_a, "b": source_b},
        sink=sink,
    )
    runner.run()

    result = sink.read_all()
    assert len(result) == 2


def test_runner_batching(tmp_path):
    """Records should be written in batches of the configured size."""
    mock_sink = Mock()
    records = [
        DatabasePlant({"scientific name": f"plant-{i}"}) for i in range(5)
    ]
    source = Mock(fetch_all=Mock(return_value=iter(records)))
    runner = Runner(
        sources={"test": source},
        sink=mock_sink,
        batch_size=2,
    )
    runner.run()

    # 2 + 2 + 1 = 3 batches
    assert mock_sink.write_batch.call_count == 3


def test_runner_retries_on_failure(tmp_path):
    """Runner should retry a source that fails."""
    mock_sink = Mock()
    source = Mock(
        fetch_all=Mock(
            side_effect=[
                RuntimeError("fail"),
                iter(
                    [
                        DatabasePlant({"scientific name": "a"}),
                    ]
                ),
            ]
        )
    )
    runner = Runner(
        sources={"test": source},
        sink=mock_sink,
        backoff_base=0.01,
    )
    runner.run()

    assert source.fetch_all.call_count == 2


def test_runner_empty_source(sink):
    """Running with an empty source should succeed without errors."""
    source = Mock(fetch_all=Mock(return_value=iter([])))
    runner = Runner(sources={"test": source}, sink=sink)
    runner.run()

    result = sink.read_all()
    assert result == []
