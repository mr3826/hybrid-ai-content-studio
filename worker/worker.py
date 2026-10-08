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
from app.core.database import check_db_health, AsyncSessionLocal
from app.repositories.job_repository import JobRepository
from app.repositories.media_repository import MediaRepository
from app.engines.core.registry import engine_registry
from app.engines.core.base import EngineContext
from app.engines.catalog import register_all_catalog_engines
from app.models.media import MediaPackage, MediaPackageStatus, SceneVoiceTrack
from sqlalchemy import select

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

        register_all_catalog_engines()
        logger.info("Engine catalog loaded in worker.")

        while self._running:
            try:
                await self.poll_and_execute()
            except Exception as e:
                logger.error(f"Error during worker loop: {e}", exc_info=True)

            await asyncio.sleep(self.poll_interval)

        logger.info("Worker process stopped cleanly.")

    async def poll_and_execute(self):
        """Poll SQLite job queue and execute next pending job."""
        async with AsyncSessionLocal() as session:
            repo = JobRepository(session)
            job = await repo.claim_next_job()
            if not job:
                return

            logger.info(f"Claimed job {job.id} (type={job.job_type}, engine={job.engine_id})")
            try:
                if job.job_type == "engine_run" and job.engine_id:
                    ctx = EngineContext(
                        run_id=job.id[:8],
                        project_id=job.project_id,
                        dry_run=job.payload.get("dry_run", False),
                        trigger="worker_job",
                        parameters=job.payload.get("parameters", {}),
                    )
                    result = await engine_registry.execute_engine(
                        job.engine_id,
                        context=ctx,
                        dry_run=ctx.dry_run,
                        session=session,
                    )
                    if job.engine_id == "media":
                        await self._persist_media_result(session, job, result)
                    if result.success:
                        await repo.complete_job(job.id, result_data=result.model_dump(mode="json"))
                        logger.info(f"Job {job.id} completed successfully.")
                    else:
                        await repo.fail_job(
                            job.id,
                            error_message=result.summary or "Engine execution failed",
                            result_data=result.model_dump(mode="json"),
                        )
                        logger.warning(f"Job {job.id} failed: {result.summary}")
                else:
                    # Echo / Generic task processing
                    await repo.complete_job(job.id, result_data={"processed": True, "payload": job.payload})
                    logger.info(f"Job {job.id} processed generically.")
            except Exception as exc:
                logger.error(f"Exception executing job {job.id}: {exc}", exc_info=True)
                await repo.fail_job(job.id, error_message=str(exc))

    async def _persist_media_result(self, session, job, result):
        """Persist media engine state before the queue job is completed or failed."""
        if (job.payload or {}).get("dry_run"):
            # A simulated health check has no media artifact and must never mutate package state.
            return
        parameters = (job.payload or {}).get("parameters", {})
        package_id = parameters.get("package_id")
        if not package_id:
            return
        stmt = select(MediaPackage).where(MediaPackage.id == package_id)
        query = await session.execute(stmt)
        package = query.scalar_one_or_none()
        if package is None:
            logger.error("Media worker result references missing package %s", package_id)
            return

        output = result.outputs[0] if result.outputs else {}
        if not output.get("status") and not output.get("quality_report"):
            package.status = MediaPackageStatus.FAILED
            package.video_path = None
            package.timeline_path = None
            package.quality_checks = {
                "passed": False,
                "production_eligible": False,
                "issues": result.errors or ["Media engine returned no verified output."],
            }
            await session.commit()
            return
        quality = output.get("quality_report") or {
            "passed": False,
            "production_eligible": False,
            "issues": result.errors or [result.summary],
        }
        package.status = output.get("status") or (MediaPackageStatus.READY if result.success else MediaPackageStatus.FAILED)
        if not result.success and package.status not in {MediaPackageStatus.MOCK, MediaPackageStatus.FAILED}:
            package.status = MediaPackageStatus.FAILED
        package.audio_path = output.get("audio_path") or package.audio_path
        package.subtitle_path = output.get("subtitle_path") or package.subtitle_path
        package.video_path = output.get("video_path")
        package.timeline_path = output.get("timeline_path")
        package.total_duration_sec = float(output.get("total_duration_sec") or package.total_duration_sec or 0.0)
        package.quality_checks = quality

        voice_config = parameters.get("voice_config") or package.voice_settings or {}
        if "audio_is_mock" in output:
            resolved_mock_mode = bool(output["audio_is_mock"])
        else:
            resolved_mock_mode = (package.voice_settings or {}).get("resolved_mock_mode")
        synthesis_modes = sorted({
            str(track.get("synthesis_mode"))
            for track in output.get("voice_tracks", [])
            if track.get("synthesis_mode")
        })
        package.voice_settings = {
            **voice_config,
            "resolved_mock_mode": resolved_mock_mode,
            "synthesis_modes": synthesis_modes,
        }

        tracks = output.get("voice_tracks") or []
        if tracks:
            media_repo = MediaRepository(session)
            await media_repo.clear_voice_tracks(package.id)
            for track in tracks:
                session.add(SceneVoiceTrack(
                    media_package_id=package.id,
                    scene_id=track["scene_id"],
                    audio_path=track["audio_path"],
                    duration_sec=float(track["duration_sec"]),
                    word_count=int(track.get("word_count", 0)),
                    waveform_peaks=track.get("waveform_peaks") or [],
                ))
        await session.commit()

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
