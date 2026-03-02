"""FastAPI application for plant lookup."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from appdirs import user_cache_dir
from attrs import define, field
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

from permaculture.data import unflatten
from permaculture.database import Database


def group_characteristics(data):
    """Group flat characteristics into a presentation-friendly structure.

    Sub-keys where all values are True are collected into a list:
    ``{"sun/partial": True, "sun/full": True}`` becomes ``{"sun": ["partial", "full"]}``.
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


def _default_db_path():
    return Path(user_cache_dir("permaculture")) / "permaculture.db"


@define
class State:
    """Mutable application state holding the database."""

    database: Database | None = field(default=None)


state = State()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Open the local database on startup."""
    db_path = _default_db_path()
    if db_path.exists():
        state.database = Database(db_path)
    yield


app = FastAPI(title="Permaculture", docs_url="/api/docs", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
def index():
    """Serve the typeahead search page."""
    html = Path(__file__).with_name("index.html").read_text()
    return HTMLResponse(html)


@app.get("/api/plants")
def suggest(
    q: str = Query(min_length=1, description="Search prefix"),
    limit: int = Query(default=10, ge=1, le=100),
):
    """Return typeahead suggestions for the given prefix."""
    if state.database is None:
        return []

    return state.database.suggest(q, limit)


@app.get("/api/plants/{scientific_name}")
def get_plant(scientific_name: str):
    """Return full characteristics for a scientific name."""
    if state.database is None:
        return {}

    plants = list(state.database.lookup([scientific_name], score=1.0))
    if not plants:
        return {}

    return group_characteristics(dict(plants[0].items()))
