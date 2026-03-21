"""Unit tests for the cli module."""

import logging
from unittest.mock import patch

import pytest

from permaculture.cli import (
    command_iterate,
    command_list,
    command_lookup,
    command_search,
    load_database,
    main,
    make_args_parser,
    make_config_parser,
)
from permaculture.database import Database
from permaculture.plant import IngestorPlant


def test_make_args_parser_command(unique):
    """Making an args parser should parse known commands."""
    args_parser = make_args_parser()
    args, _ = args_parser.parse_known_args(["lookup", unique("text")])
    assert args.command == "lookup"


def test_make_args_parser_ingest():
    """Making an args parser should parse the ingest command."""
    args_parser = make_args_parser()
    args, _ = args_parser.parse_known_args(["ingest"])
    assert args.command == "ingest"


def test_make_args_parser_command_error(unique):
    """Making an args parser should raise on unknown commands."""
    args_parser = make_args_parser()
    with pytest.raises(SystemExit):
        args_parser.parse_known_args(["test"])


def test_make_args_parser_remaining(unique):
    """Making an args parser should have remaining args."""
    args_parser = make_args_parser()
    _, remaining = args_parser.parse_known_args(
        ["--log-level=debug", "lookup", unique("text")]
    )
    assert remaining == ["--log-level=debug"]


def test_make_config_parser_defaults():
    """Making a config parser should have sensible defaults."""
    config_parser = make_config_parser([])
    config = config_parser.parse_args([])
    assert config.log_level == logging.WARNING


def test_make_config_parser_args():
    """Making a config parser should parse args."""
    config_parser = make_config_parser([])
    config = config_parser.parse_args(["--log-level=debug"])
    assert config.log_level == logging.DEBUG


def test_make_config_parser_files(tmpdir):
    """Making a config parser should parse files."""
    path = tmpdir / ".permaculture"
    path.write_text("log-level = debug", encoding="utf8")
    config_parser = make_config_parser([path])
    config = config_parser.parse_args([])
    assert config.log_level == logging.DEBUG


def test_make_config_parser_env(monkeypatch):
    """Making a config parser should read PERMACULTURE_ env vars."""
    monkeypatch.setenv("PERMACULTURE_NC_PASSWORD", "secret")
    config_parser = make_config_parser([])
    config = config_parser.parse_args([])
    assert config.nc_password == "secret"  # noqa: S105


def test_make_config_parser_nc_password_file(tmpdir):
    """Making a config parser should accept --nc-password-file."""
    config_parser = make_config_parser([])
    password_file = tmpdir / "secret"
    password_file.write_text("secret", encoding="utf8")
    config = config_parser.parse_args([f"--nc-password-file={password_file}"])
    assert config.nc_password_file == str(password_file)


@patch("sys.stdout")
def test_main_help(stdout):
    """The main function should output usage when asked for --help."""
    with pytest.raises(SystemExit):
        main(["--help"])

    assert "usage" in stdout.write.call_args[0][0]


@patch("sys.stderr")
def test_main_error(stderr, unique):
    """The main function should output an error with an invalid command."""
    with pytest.raises(SystemExit):
        main([unique("text")])

    assert "invalid choice" in stderr.write.call_args[0][0]


@pytest.fixture
def database():
    """Create a populated in-memory database for CLI testing."""
    db = Database.from_url(":memory:")
    db.initialize()
    db.write_batch(
        [
            IngestorPlant(
                {
                    "scientific name": "symphytum officinale",
                    "common name/comfrey": True,
                    "edibility": 3,
                },
                1.0,
                ingestor="pfaf",
                title="Plants For A Future",
                source="https://pfaf.org/",
            ),
            IngestorPlant(
                {
                    "scientific name": "achillea millefolium",
                    "common name/yarrow": True,
                },
                1.0,
                ingestor="pfaf",
                title="Plants For A Future",
                source="https://pfaf.org/",
            ),
        ]
    )
    return db


def test_make_args_parser_iterate():
    """Making an args parser should parse the iterate command."""
    args_parser = make_args_parser()
    args, _ = args_parser.parse_known_args(["iterate"])
    assert args.command == "iterate"


def test_make_args_parser_list():
    """Making an args parser should parse the list command."""
    args_parser = make_args_parser()
    args, _ = args_parser.parse_known_args(["list"])
    assert args.command == "list"


def test_make_args_parser_search(unique):
    """Making an args parser should parse the search command."""
    args_parser = make_args_parser()
    args, _ = args_parser.parse_known_args(["search", unique("text")])
    assert args.command == "search"


def test_make_args_parser_ingest_defaults():
    """Making an args parser should have sensible ingest defaults."""
    args_parser = make_args_parser()
    args, _ = args_parser.parse_known_args(["ingest"])
    assert args.concurrency == 4
    assert args.retries == 3


def test_make_args_parser_ingest_custom():
    """Making an args parser should accept custom ingest options."""
    args_parser = make_args_parser()
    args, _ = args_parser.parse_known_args(
        ["ingest", "--concurrency=8", "--retries=5"]
    )
    assert args.concurrency == 8
    assert args.retries == 5


def test_make_args_parser_lookup_defaults(unique):
    """Making an args parser should have sensible lookup defaults."""
    args_parser = make_args_parser()
    name = unique("text")
    args, _ = args_parser.parse_known_args(["lookup", name])
    assert args.names == [name]
    assert args.file is False


def test_make_args_parser_lookup_multiple_names(unique):
    """Making an args parser should accept multiple lookup names."""
    args_parser = make_args_parser()
    n1, n2 = unique("text"), unique("text")
    args, _ = args_parser.parse_known_args(["lookup", n1, n2])
    assert args.names == [n1, n2]


def test_make_args_parser_search_defaults(unique):
    """Making an args parser should have sensible search defaults."""
    args_parser = make_args_parser()
    args, _ = args_parser.parse_known_args(["search", unique("text")])
    assert args.name


def test_make_config_parser_serializer():
    """Making a config parser should parse the serializer option."""
    config_parser = make_config_parser([])
    config = config_parser.parse_args(["--serializer=application/json"])
    assert config.serializer.default_content_type == "application/json"


def test_make_config_parser_ingestor():
    """Making a config parser should parse the ingestor option."""
    config_parser = make_config_parser([])
    config = config_parser.parse_args(["--ingestor=pfaf"])
    assert "pfaf" in config.ingestors


def test_command_iterate(database):
    """Iterating should return all scientific names."""
    result = command_iterate(database)
    assert sorted(result) == ["achillea millefolium", "symphytum officinale"]


def test_command_list(database):
    """Listing should return available ingestors."""
    result = command_list(database)
    assert result == ["pfaf"]


def test_command_search(database):
    """Searching should return matching plants."""
    args_parser = make_args_parser()
    args, _ = args_parser.parse_known_args(["search", "comfrey"])
    result = command_search(args, database)
    assert len(result) == 1
    assert "symphytum officinale" in result[0]


def test_command_search_no_match(database):
    """Searching for a non-existent name should return empty."""
    args_parser = make_args_parser()
    args, _ = args_parser.parse_known_args(["search", "nonexistent"])
    result = command_search(args, database)
    assert result == []


def test_command_lookup(database):
    """Looking up should return plant characteristics."""
    args_parser = make_args_parser()
    config_parser = make_config_parser([])
    args, remaining = args_parser.parse_known_args(
        ["lookup", "symphytum officinale"]
    )
    config = config_parser.parse_args(remaining)
    result = command_lookup(args, config, database)
    assert len(result) == 1
    assert "scientific name" in result[0]


def test_command_lookup_exclude(database):
    """Looking up with exclude should filter characteristics."""
    args_parser = make_args_parser()
    config_parser = make_config_parser([])
    args, remaining = args_parser.parse_known_args(
        ["lookup", "symphytum officinale", "--exclude=edib"]
    )
    config = config_parser.parse_args(remaining)
    result = command_lookup(args, config, database)
    assert len(result) == 1
    assert "edibility" not in result[0]


def test_command_lookup_include(database):
    """Looking up with include should only return matching characteristics."""
    args_parser = make_args_parser()
    config_parser = make_config_parser([])
    args, remaining = args_parser.parse_known_args(
        ["lookup", "symphytum officinale", "--include=scientific"]
    )
    config = config_parser.parse_args(remaining)
    result = command_lookup(args, config, database)
    assert len(result) == 1
    assert list(result[0].keys()) == ["scientific name"]


def test_command_lookup_file(database, tmp_path):
    """Looking up with --file should read names from the given file."""
    names_file = tmp_path / "names.txt"
    names_file.write_text("symphytum officinale\n")
    args_parser = make_args_parser()
    config_parser = make_config_parser([])
    args, remaining = args_parser.parse_known_args(
        ["lookup", "--file", str(names_file)]
    )
    config = config_parser.parse_args(remaining)
    result = command_lookup(args, config, database)
    assert len(result) == 1
    assert result[0]["scientific name"] == "symphytum officinale"


def test_command_lookup_no_match(database):
    """Looking up a non-existent name should return empty."""
    args_parser = make_args_parser()
    config_parser = make_config_parser([])
    args, remaining = args_parser.parse_known_args(
        ["lookup", "nonexistent species"]
    )
    config = config_parser.parse_args(remaining)
    result = command_lookup(args, config, database)
    assert result == []


def test_load_database_not_found(monkeypatch, tmp_path):
    """Loading a database that doesn't exist should raise SystemExit."""
    monkeypatch.setenv("PERMACULTURE_DATABASE", str(tmp_path / "missing.db"))
    with pytest.raises(SystemExit, match="Database not found"):
        load_database()


def test_load_database_exists(monkeypatch, tmp_path):
    """Loading a database that exists should succeed."""
    db_path = tmp_path / "permaculture.db"
    db = Database.from_url(str(db_path))
    db.initialize()
    monkeypatch.setenv("PERMACULTURE_DATABASE", str(db_path))
    load_database()
