"""MCP server exposing the permaculture plant database."""

import os

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from permaculture.database import Database
from permaculture.locales import all_aliases


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


_OPERATORS_BY_TYPE = {
    "text": ["eq"],
    "bool": ["eq"],
    "int": ["eq", "lt", "lte", "gt", "gte"],
    "float": ["eq", "lt", "lte", "gt", "gte"],
}


def list_characteristics_in(database) -> dict:
    """Build a structured schema of all searchable plant characteristics."""
    aliases = all_aliases()
    fields = []
    for char in database.list_characteristics():
        typ = char["type"]
        field = {
            "key": char["key"],
            "type": typ,
            "operators": _OPERATORS_BY_TYPE[typ],
            "count": char["count"],
        }
        if typ in ("int", "float"):
            field["min"] = char["min"]
            field["max"] = char["max"]
        if char["key"] in aliases:
            field["aliases"] = aliases[char["key"]]
        if "examples" in char:
            field["examples"] = char["examples"]
        fields.append(field)

    return {
        "entity": "plant",
        "fields": fields,
    }


def search_plants_in(
    database,
    name: str | None = None,
    *,
    filters: dict | None = None,
    limit: int = 10,
    offset: int = 0,
) -> dict:
    """Search for plants by common or scientific name."""
    if filters:
        valid_keys = {c["key"] for c in database.list_characteristics()}
        unknown = sorted(k for k in filters if k not in valid_keys)
        if unknown:
            return {
                "error": f"Unknown filter keys: {', '.join(unknown)}",
                "hint": "Call list_plant_characteristics to see valid keys.",
            }
    total_count = database.search_count(name=name, filters=filters)
    results = [
        {
            "scientific_name": plant.scientific_name,
            "common_names": plant.common_names,
        }
        for plant in database.search(
            name=name, filters=filters, limit=limit, offset=offset,
        )
    ]
    return {
        "total_count": total_count,
        "results": results,
    }


def lookup_plants_in(database, names: list[str]) -> list[dict]:
    """Look up plant characteristics by exact scientific name."""
    return [
        {
            "scientific_name": plant.scientific_name,
            "common_names": plant.common_names,
            "data": dict(plant),
            "ingestors": plant.ingestors,
            "sources": plant.sources,
        }
        for plant in database.lookup(names)
    ]


@mcp.tool()
def list_plant_characteristics() -> dict:
    """Return the plant schema: filterable fields, types, and supported operators.

    Use this before calling search_plants to discover valid filter keys and
    the operators each field supports.  The response includes:
    - ``version``: schema version date
    - ``filter_syntax``: supported logical and comparison operators
    - ``fields``: one entry per filterable characteristic with key, type,
      operators, count, and (for text fields) example values
    """
    database = Database.from_env()
    return list_characteristics_in(database)


@mcp.tool()
def search_plants(
    name: str | None = None,
    filters: dict | None = None,
    limit: int = 10,
    offset: int = 0,
) -> dict:
    """Search for plants by name and/or characteristics.

    Before constructing filters from natural-language criteria,
    first inspect available characteristics and exact field names with
    list_plant_characteristics, unless the user already supplied valid
    schema keys.

    Returns up to ``limit`` results (default 10, max 100) starting from
    ``offset``.  The response includes ``total_count`` so you can tell
    whether more results are available.

    Args:
        name: Common or scientific name to search for.
        filters: Filter by characteristics. Use {"key": value} for
            exact matches, or {"key": {"gt": v, "lte": v}} for
            numeric ranges.
            Call list_plant_characteristics to discover available keys.
        limit: Maximum number of results to return (default 10, max 100).
        offset: Number of results to skip (default 0).
    """
    database = Database.from_env()
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    return search_plants_in(
        database, name, filters=filters, limit=limit, offset=offset,
    )


@mcp.tool()
def lookup_plants(
    names: list[str],
) -> list[dict]:
    """Look up plant characteristics by exact scientific name.

    Args:
        names: Scientific names to look up.
    """
    database = Database.from_env()
    return lookup_plants_in(database, names)
