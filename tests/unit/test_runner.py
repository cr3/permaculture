"""Unit tests for the runner module."""

from unittest.mock import Mock

from permaculture.plant import IngestorPlant
from permaculture.runner import Runner


def test_runner_ingest_single_source(database):
    """Running with a single source should write all records."""
    records = [
        IngestorPlant({"scientific name": "symphytum officinale"}, 1.0, ingestor="test", title="Test", source="s"),
        IngestorPlant({"scientific name": "achillea millefolium"}, 1.0, ingestor="test", title="Test", source="s"),
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
                    IngestorPlant({"scientific name": "a"}, 1.0, ingestor="a", title="A", source="s"),
                ]
            )
        )
    )
    source_b = Mock(
        fetch_all=Mock(
            return_value=iter(
                [
                    IngestorPlant({"scientific name": "b"}, 1.0, ingestor="b", title="B", source="s"),
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
        IngestorPlant({"scientific name": f"plant-{i}"}, 1.0, ingestor="test", title="Test", source="s") for i in range(5)
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
                        IngestorPlant({"scientific name": "a"}, 1.0, ingestor="test", title="Test", source="s"),
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


def test_runner_idempotent(database):
    """Running the same ingestor twice should not create duplicates."""
    def make_source():
        return Mock(
            fetch_all=Mock(
                return_value=iter(
                    [
                        IngestorPlant({"scientific name": "a"}, 1.0, ingestor="test", title="Test", source="s"),
                        IngestorPlant({"scientific name": "b"}, 1.0, ingestor="test", title="Test", source="s"),
                    ]
                )
            )
        )

    Runner(sources={"test": make_source()}, database=database).run()
    Runner(sources={"test": make_source()}, database=database).run()

    result = list(database.iterate())
    assert len(result) == 2


def test_runner_preserves_other_ingestors(database):
    """Running one ingestor should not affect data from another."""
    source_a = Mock(
        fetch_all=Mock(
            return_value=iter(
                [IngestorPlant({"scientific name": "x"}, 1.0, ingestor="a", title="A", source="s")]
            )
        )
    )
    Runner(sources={"a": source_a}, database=database).run()

    source_b = Mock(
        fetch_all=Mock(
            return_value=iter(
                [IngestorPlant({"scientific name": "y"}, 1.0, ingestor="b", title="B", source="s")]
            )
        )
    )
    Runner(sources={"b": source_b}, database=database).run()

    result = list(database.iterate())
    assert len(result) == 2
    names = {p.scientific_name for p in result}
    assert names == {"x", "y"}
