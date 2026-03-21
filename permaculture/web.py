"""FastAPI application for plant lookup."""

import argparse
from contextlib import asynccontextmanager
from importlib.resources import files
from itertools import islice
from typing import Annotated

from fastapi import Depends, FastAPI, Query
from fastapi.responses import HTMLResponse

from permaculture.data import sort_data, unflatten
from permaculture.database import Database
from permaculture.locales import Locales
from permaculture.mcp_server import mcp


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


# Used by test client dependency overrides.
def get_database():
    return Database.from_env()


DatabaseDep = Annotated[Database, Depends(get_database)]

@asynccontextmanager
async def lifespan(app):
    async with mcp.session_manager.run():
        yield

app = FastAPI(title="Permaculture", docs_url="/permaculture/docs", lifespan=lifespan)

mcp.settings.streamable_http_path = "/"
app.mount("/permaculture/mcp", mcp.streamable_http_app())


@app.get("/permaculture/plants")
def get_plants(
    database: DatabaseDep,
    q: str = Query(min_length=1, description="Search query"),
    limit: int = Query(default=10, ge=1, le=100),
    lang: str = Query(default="en", description="Language for translated names"),
):
    """Return search results for the given query."""
    locales = Locales.from_domain("api", language=lang)
    return [locales.translate_data(
            {
                "scientific name": plant.scientific_name,
                "common name": plant.common_names,
            },
        )
        for plant in islice(database.search(name=q), limit)
    ]


@app.get("/permaculture/plants/{scientific_name}")
def get_plant(
    scientific_name: str,
    database: DatabaseDep,
    lang: str = Query(default="en", description="Language for translated keys"),
):
    """Return full characteristics for a scientific name."""
    plants = list(database.lookup([scientific_name]))
    if not plants:
        return {}

    locales = Locales.from_domain("api", language=lang)
    plant = plants[0]
    data = group_characteristics(dict(plant.items()))
    translated = sort_data(locales.translate_data(data))
    return {
        **translated,
        "sources": locales.translate_data(unflatten(plant.sources)),
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
    uvicorn.run("permaculture.web:app", host=args.host, port=args.port, reload=args.reload)
