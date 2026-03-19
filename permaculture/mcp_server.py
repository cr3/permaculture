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
