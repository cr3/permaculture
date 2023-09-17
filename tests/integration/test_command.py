"""Integration tests for the command module."""

from subprocess import check_output


def test_main_help():
    """Calling the permaculture command with --help should return the usage."""
    output = check_output(
        ["permaculture", "--help"], universal_newlines=True  # noqa: S603, S607
    )
    assert "usage" in output
