"""Runner for orchestrating ingestion from sources into a sink."""

import asyncio
import logging

from attrs import define, field

from permaculture.ingestor import Ingestor
from permaculture.sink import Sink

logger = logging.getLogger(__name__)

BATCH_SIZE = 500


@define(frozen=True)
class Runner:
    """Orchestrates ingestion from multiple sources into a sink.

    :param sources: Mapping of name to ingestor.
    :param sink: Destination sink for plant records.
    :param max_concurrency: Maximum parallel source ingestions.
    :param max_retries: Maximum retry attempts per source.
    :param backoff_base: Base for exponential backoff in seconds.
    :param batch_size: Records per batch write.
    """

    sources: dict[str, Ingestor] = field(factory=dict)
    sink: Sink = field(factory=dict)
    max_concurrency: int = field(default=4)
    max_retries: int = field(default=3)
    backoff_base: float = field(default=2.0)
    batch_size: int = field(default=BATCH_SIZE)

    def run(self):
        """Run ingestion synchronously."""
        self.sink.initialize()
        asyncio.run(self._run_async())

    async def _run_async(self):
        sem = asyncio.Semaphore(self.max_concurrency)
        tasks = [
            self._ingest_source(name, source, sem)
            for name, source in self.sources.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for name, result in zip(self.sources, results):
            if isinstance(result, Exception):
                logger.error(
                    "Failed ingesting %(name)s: %(error)s",
                    {"name": name, "error": result},
                )

    async def _ingest_source(self, name, source, sem):
        async with sem:
            for attempt in range(self.max_retries):
                try:
                    await asyncio.to_thread(self._ingest_sync, name, source)
                    logger.info(
                        "Finished ingesting %(name)s",
                        {"name": name},
                    )
                    return
                except Exception:
                    wait = self.backoff_base**attempt
                    logger.warning(
                        "Retry %(attempt)s for %(name)s"
                        " (waiting %(wait)ss)",
                        {
                            "attempt": attempt + 1,
                            "name": name,
                            "wait": wait,
                        },
                    )
                    await asyncio.sleep(wait)

            raise RuntimeError(f"Failed ingesting {name}")

    def _ingest_sync(self, name, source):
        batch = []
        for record in source.fetch_all():
            batch.append(record)
            if len(batch) >= self.batch_size:
                self.sink.write_batch(name, batch)
                batch.clear()

        if batch:
            self.sink.write_batch(name, batch)
