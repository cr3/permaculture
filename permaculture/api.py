"""FastAPI application for plant lookup."""

import argparse
from contextlib import suppress
from importlib.resources import files
from itertools import islice
from typing import Annotated

from fastapi import Depends, FastAPI, Query
from fastapi.responses import HTMLResponse

from permaculture.data import unflatten
from permaculture.database import Database
from permaculture.locales import Locales


def group_characteristics(data):
    """Group flat characteristics into a presentation-friendly structure.

    Sub-keys where all values are True are collected into a list:
    ``{"sun/partial": True, "sun/full": True}`` becomes
    ``{"sun": ["partial", "full"]}``.
    """
    nested = unflatten(data)
    if not isinstance(nested, dict):
        return nested

    return {
        key: (
            sorted(value)
            if isinstance(value, dict)
            and all(v is True for v in value.values())
            else value
        )
        for key, value in nested.items()
    }


def translate_keys(data, locales):
    """Recursively translate dictionary keys using locales."""
    if not isinstance(data, dict):
        return data

    return {
        locales.translate(key): (
            translate_keys(value, locales)
            if isinstance(value, dict)
            else value
        )
        for key, value in data.items()
    }


def get_database():
    # Used by test client dependency overrides.
    return Database.from_env()


DatabaseDep = Annotated[Database, Depends(get_database)]


app = FastAPI(title="Permaculture", docs_url="/permaculture/docs")

with suppress(ImportError):
    from permaculture.mcp_server import mcp

    app.mount("/permaculture/mcp", mcp.sse_app(mount_path="/permaculture/mcp"))


@app.get("/permaculture/plants")
def get_plants(
    database: DatabaseDep,
    q: str = Query(min_length=1, description="Search query"),
    limit: int = Query(default=10, ge=1, le=100),
    lang: str = Query(default="en", description="Language for translated names"),
    score: float = Query(default=0.6, ge=0, le=1, description="Minimum match score"),
):
    """Return search results for the given query."""
    locales = Locales.from_domain("api", language=lang)
    return [translate_keys(
            {
                "scientific name": plant.scientific_name,
                "common name": plant.common_names,
            },
            locales,
        )
        for plant in islice(database.search(q, score=score), limit)
    ]


@app.get("/permaculture/plants/{scientific_name}")
def get_plant(
    scientific_name: str,
    database: DatabaseDep,
    lang: str = Query(default="en", description="Language for translated keys"),
):
    """Return full characteristics for a scientific name."""
    plants = list(database.lookup([scientific_name], score=1.0))
    if not plants:
        return {}

    locales = Locales.from_domain("api", language=lang)
    plant = plants[0]
    data = group_characteristics(dict(plant.items()))
    return {
        **translate_keys(data, locales),
        "sources": plant.sources,
        "ingestors": plant.ingestors,
    }


@app.get("/permaculture/", response_class=HTMLResponse)
def index():
    """Serve the minimal web interface."""
    return files("permaculture.static").joinpath("index.html").read_text()


def main():
    """Entry point for the permaculture web server."""
    import uvicorn

    parser = argparse.ArgumentParser(
        description="Permaculture web server",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="bind address (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="port (default: 8000)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="auto-reload",
    )
    args = parser.parse_args()
    uvicorn.run("permaculture.api:app", host=args.host, port=args.port, reload=args.reload)
