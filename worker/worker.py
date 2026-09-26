import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add project root to sys.path so worker can import app modules
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "apps" / "api"))
sys.path.insert(0, str(ROOT_DIR))

from app.core.config import settings
from app.core.database import check_db_health

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] [worker]: %(message)s",
)
logger = logging.getLogger("studio.worker")


class StudioWorker:
    def __init__(self, poll_interval: float = 2.0):
        self.poll_interval = poll_interval
        self._running = False

    async def start(self):
        self._running = True
        logger.info(f"Studio Background Worker started (poll_interval={self.poll_interval}s).")
        logger.info("Verifying database connectivity...")

        db_ok = await check_db_health()
        if db_ok:
            logger.info("Worker database connection verified (SQLite WAL).")
        else:
            logger.warning("Worker could not verify database connection at startup.")

        while self._running:
            try:
                await self.poll_and_execute()
            except Exception as e:
                logger.error(f"Error during worker loop: {e}", exc_info=True)

            await asyncio.sleep(self.poll_interval)

        logger.info("Worker process stopped cleanly.")

    async def poll_and_execute(self):
        # Phase 0: Heartbeat check; future phases poll job queues for TTS, FFmpeg, and batch fetches
        pass

    def stop(self):
        logger.info("Stop signal received. Shutting down worker...")
        self._running = False


async def main():
    worker = StudioWorker(poll_interval=2.0)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, worker.stop)
        except NotImplementedError:
            # Signal handling on Windows event loop fallback
            pass

    await worker.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user.")
