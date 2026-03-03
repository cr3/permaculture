"""Unit tests for the cli module."""

import logging
from unittest.mock import patch

import pytest

from permaculture.cli import (
    main,
    make_args_parser,
    make_config_parser,
)


def test_make_args_parser_command(unique):
    """Making an args parser should parse known commands."""
    args_parser = make_args_parser()
    args, _ = args_parser.parse_known_args(["lookup", unique("text")])
    assert args.command == "lookup"


def test_make_args_parser_ingest_no_ingestors():
    """Making an args parser should default to no ingestors."""
    args_parser = make_args_parser()
    args, _ = args_parser.parse_known_args(["ingest"])
    assert args.ingestors == []


def test_make_args_parser_ingest_with_ingestors():
    """Making an args parser should accept ingestor names."""
    args_parser = make_args_parser()
    args, _ = args_parser.parse_known_args(["ingest", "nc", "pfaf"])
    assert args.ingestors == ["nc", "pfaf"]


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


def test_main_store(tmpdir):
    """Storing a file should create a key under the storage directory."""
    storage = tmpdir.join("storage")
    file = tmpdir.join("file").ensure()
    main(
        [
            f"--storage={storage}",
            "--log-level=debug",
            "store",
            "key",
            str(file),
        ]
    )
    assert storage.join("key").exists()


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
