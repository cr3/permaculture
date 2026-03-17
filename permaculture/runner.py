"""Runner for orchestrating ingestion from sources into a database."""

import asyncio
import logging
import random

from attrs import define, field

from permaculture.database import Database
from permaculture.plant import IngestorPlant
from permaculture.ingestor import Ingestor

logger = logging.getLogger(__name__)

BATCH_SIZE = 500
QUEUE_SIZE = 5000


@define(frozen=True)
class Runner:
    """Orchestrates ingestion from multiple sources into a database.

    Writes are serialized through a bounded async queue so that only
    one coroutine touches the database, avoiding SQLite lock errors.

    :param sources: Mapping of name to ingestor.
    :param database: Destination database for plant records.
    :param max_concurrency: Maximum parallel source ingestions.
    :param max_retries: Maximum retry attempts per source.
    :param backoff_base: Base for exponential backoff in seconds.
    :param backoff_cap: Maximum backoff delay in seconds.
    :param batch_size: Records per batch write.
    :param queue_size: Maximum pending observations before backpressure.
    """

    database: Database = field()
    sources: dict[str, Ingestor] = field(factory=dict)
    max_concurrency: int = field(default=4)
    max_retries: int = field(default=3)
    backoff_base: float = field(default=0.25)
    backoff_cap: float = field(default=10.0)
    batch_size: int = field(default=BATCH_SIZE)
    queue_size: int = field(default=QUEUE_SIZE)

    def run(self):
        """Run ingestion synchronously."""
        self.database.initialize()
        asyncio.run(self._run_async())

    async def _run_async(self):
        queue: asyncio.Queue[IngestorPlant | None] = asyncio.Queue(
            maxsize=self.queue_size
        )
        loop = asyncio.get_running_loop()

        writer_task = asyncio.create_task(self._writer(queue))

        sem = asyncio.Semaphore(self.max_concurrency)
        tasks = [
            self._ingest_source(name, source, sem, queue, loop)
            for name, source in self.sources.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for name, result in zip(self.sources, results, strict=False):
            if isinstance(result, Exception):
                error = result.__cause__ or result
                logger.error(
                    "Failed ingesting %(name)s: %(error)s",
                    {"name": name, "error": error},
                )
                logger.debug(
                    "Traceback for %(name)s",
                    {"name": name},
                    exc_info=result,
                )

        await queue.put(None)
        await writer_task

    async def _writer(self, queue):
        """Drain the queue and write batches to the database."""
        buffer: list[IngestorPlant] = []
        while True:
            item = await queue.get()
            if item is None:
                break

            buffer.append(item)
            if len(buffer) >= self.batch_size:
                self.database.write_batch(buffer)
                buffer = []

        if buffer:
            self.database.write_batch(buffer)

    async def _ingest_source(self, name, source, sem, queue, loop):
        async with sem:
            last_exc = None
            for attempt in range(self.max_retries):
                try:
                    await asyncio.to_thread(
                        self._ingest_sync, source, queue, loop
                    )
                except Exception as exc:
                    last_exc = exc
                    wait = self._backoff_seconds(attempt + 1)
                    logger.warning(
                        "Retry %(attempt)s for %(name)s (waiting %(wait)ss)",
                        {
                            "attempt": attempt + 1,
                            "name": name,
                            "wait": wait,
                        },
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.info(
                        "Finished ingesting %(name)s",
                        {"name": name},
                    )
                    return

            raise RuntimeError(f"Failed ingesting {name}") from last_exc

    def _backoff_seconds(self, attempt):
        """Exponential backoff with jitter."""
        exp = min(self.backoff_cap, self.backoff_base * (2 ** (attempt - 1)))
        return random.random() * exp  # noqa: S311

    def _ingest_sync(self, source, queue, loop):
        for record in source.fetch_all():
            asyncio.run_coroutine_threadsafe(queue.put(record), loop).result()
