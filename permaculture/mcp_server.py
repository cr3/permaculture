"""MCP server exposing the permaculture plant database."""

import argparse
import logging

from mcp.server.fastmcp import FastMCP

from permaculture.database import Database

logger = logging.getLogger(__name__)

mcp = FastMCP("permaculture")


def _plant_dict(plant):
    return {
        "scientific_name": plant.scientific_name,
        "common_names": plant.common_names,
        "data": dict(plant),
        "ingestors": plant.ingestors,
        "sources": plant.sources,
    }


def search_plants_in(database, name: str, score: float = 0.7) -> list[dict]:
    """Search for plants by common or scientific name."""
    return [_plant_dict(plant) for plant in database.search(name, score)]


def lookup_plants_in(database, names: list[str], score: float = 1.0) -> list[dict]:
    """Look up plant characteristics by exact scientific name."""
    return [_plant_dict(plant) for plant in database.lookup(names, score)]


@mcp.tool()
def search_plants(name: str, score: float = 0.7) -> list[dict]:
    """Search for plants by common or scientific name.

    Args:
        name: Common or scientific name to search for.
        score: Minimum match score from 0.0 to 1.0 (default 0.7).
    """
    database = Database.from_env()
    return search_plants_in(database, name, score)


@mcp.tool()
def lookup_plants(
    names: list[str], score: float = 1.0
) -> list[dict]:
    """Look up plant characteristics by exact scientific name.

    Args:
        names: Scientific names to look up.
        score: Minimum match score from 0.0 to 1.0 (default 1.0).
    """
    database = Database.from_env()
    return lookup_plants_in(database, names, score)



def main():
    """Entry point for the permaculture MCP server."""
    parser = argparse.ArgumentParser(
        description="Permaculture MCP server",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="transport protocol (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="host for SSE transport (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="port for SSE transport (default: 8000)",
    )
    args = parser.parse_args()
    mcp.run(transport=args.transport, host=args.host, port=args.port)
