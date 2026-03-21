"""MCP server exposing the permaculture plant database."""

import os

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from permaculture.database import Database


def get_allowed_hosts(env=os.environ):
    allowed_hosts=[
        "localhost:*",
        "127.0.0.1:*",
    ]
    if "SERVER_IP" in env:
        server_ip = env["SERVER_IP"]
        allowed_hosts.append(
            f"{server_ip}:*",
        )
    if "SERVER_HOSTNAME" in env:
        server_hostname = env["SERVER_HOSTNAME"]
        allowed_hosts.extend([
            server_hostname,
            f"{server_hostname}:*",
        ])
    return allowed_hosts


def get_allowed_origins(env=os.environ):
    allowed_origins=[
        "http://localhost:*",
    ]
    if "SERVER_HOSTNAME" in env:
        server_hostname = env["SERVER_HOSTNAME"]
        allowed_origins.extend([
            f"http://{server_hostname}",
            f"http://{server_hostname}:*",
        ])
    return allowed_origins


mcp = FastMCP(
    "Permaculture",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=get_allowed_hosts(),
        allowed_origins=get_allowed_origins(),
    ),
)


def _plant_dict(plant):
    return {
        "scientific_name": plant.scientific_name,
        "common_names": plant.common_names,
        "data": dict(plant),
        "ingestors": plant.ingestors,
        "sources": plant.sources,
    }


def list_characteristics_in(database) -> list[dict]:
    """List all searchable plant characteristics."""
    return database.list_characteristics()


def search_plants_in(
    database,
    name: str | None = None,
    score: float = 0.7,
    *,
    filters: dict | None = None,
) -> list[dict]:
    """Search for plants by common or scientific name."""
    return [
        _plant_dict(plant)
        for plant in database.search(
            name=name, score=score, filters=filters,
        )
    ]


def lookup_plants_in(database, names: list[str], score: float = 1.0) -> list[dict]:
    """Look up plant characteristics by exact scientific name."""
    return [_plant_dict(plant) for plant in database.lookup(names, score)]


@mcp.tool()
def list_plant_characteristics() -> list[dict]:
    """List all searchable plant characteristics with types and counts.

    Returns keys that can be used as filters in search_plants.
    Each entry includes the key name, value type (number or text),
    and count of plants with that characteristic.
    Numeric keys also include min and max values.
    """
    database = Database.from_env()
    return list_characteristics_in(database)


@mcp.tool()
def search_plants(
    name: str | None = None,
    filters: dict | None = None,
    score: float = 0.7,
) -> list[dict]:
    """Search for plants by name and/or characteristics.

    Args:
        name: Common or scientific name to search for.
        filters: Filter by characteristics. Use {"key": value} for
            exact matches, or {"key": {"gt": v, "lte": v}} for
            numeric ranges.
            Call list_plant_characteristics to discover available keys.
        score: Minimum match score from 0.0 to 1.0 (default 0.7).
    """
    database = Database.from_env()
    return search_plants_in(database, name, score, filters=filters)


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
