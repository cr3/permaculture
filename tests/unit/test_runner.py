"""Unit tests for the runner module."""

from unittest.mock import Mock

import pytest

from permaculture.database import Database
from permaculture.plant import IngestorPlant
from permaculture.runner import Runner


@pytest.fixture
def database(tmp_path):
    """Create a Database backed by a temporary file."""
    db = Database(tmp_path / "test.db")
    db.initialize()
    return db


def test_runner_ingest_single_source(database):
    """Running with a single source should write all records."""
    records = [
        IngestorPlant({"scientific name": "symphytum officinale"}, ingestor="test", title="Test", source="s"),
        IngestorPlant({"scientific name": "achillea millefolium"}, ingestor="test", title="Test", source="s"),
    ]
    source = Mock(fetch_all=Mock(return_value=iter(records)))
    runner = Runner(sources={"test": source}, database=database)
    runner.run()

    result = list(database.iterate())
    assert len(result) == 2


def test_runner_ingest_multiple_sources(database):
    """Running with multiple sources should write all records."""
    source_a = Mock(
        fetch_all=Mock(
            return_value=iter(
                [
                    IngestorPlant({"scientific name": "a"}, ingestor="a", title="A", source="s"),
                ]
            )
        )
    )
    source_b = Mock(
        fetch_all=Mock(
            return_value=iter(
                [
                    IngestorPlant({"scientific name": "b"}, ingestor="b", title="B", source="s"),
                ]
            )
        )
    )
    runner = Runner(
        sources={"a": source_a, "b": source_b},
        database=database,
    )
    runner.run()

    result = list(database.iterate())
    assert len(result) == 2


def test_runner_batching(tmp_path):
    """Records should be written in batches of the configured size."""
    mock_database = Mock()
    records = [
        IngestorPlant({"scientific name": f"plant-{i}"}, ingestor="test", title="Test", source="s") for i in range(5)
    ]
    source = Mock(fetch_all=Mock(return_value=iter(records)))
    runner = Runner(
        sources={"test": source},
        database=mock_database,
        batch_size=2,
    )
    runner.run()

    total_written = sum(
        len(call.args[0]) for call in mock_database.write_batch.call_args_list
    )
    assert total_written == 5
    for call in mock_database.write_batch.call_args_list:
        assert len(call.args[0]) <= 2


def test_runner_retries_on_failure(tmp_path):
    """Runner should retry a source that fails."""
    mock_database = Mock()
    source = Mock(
        fetch_all=Mock(
            side_effect=[
                RuntimeError("fail"),
                iter(
                    [
                        IngestorPlant({"scientific name": "a"}, ingestor="test", title="Test", source="s"),
                    ]
                ),
            ]
        )
    )
    runner = Runner(
        sources={"test": source},
        database=mock_database,
        backoff_base=0.01,
    )
    runner.run()

    assert source.fetch_all.call_count == 2


def test_runner_empty_source(database):
    """Running with an empty source should succeed without errors."""
    source = Mock(fetch_all=Mock(return_value=iter([])))
    runner = Runner(sources={"test": source}, database=database)
    runner.run()

    result = list(database.iterate())
    assert result == []
