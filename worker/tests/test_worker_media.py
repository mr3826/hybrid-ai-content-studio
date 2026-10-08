from types import SimpleNamespace

import pytest

from app.engines.core.base import EngineResult
from worker.worker import StudioWorker


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _Session:
    def __init__(self, package):
        self.package = package
        self.execute_calls = 0
        self.commit_calls = 0

    async def execute(self, _statement):
        self.execute_calls += 1
        return _ScalarResult(self.package)

    async def commit(self):
        self.commit_calls += 1


def _package():
    return SimpleNamespace(
        id="package-1",
        status="RENDERING",
        audio_path="data/assets/audio/old.wav",
        subtitle_path="data/assets/subtitles/old.srt",
        video_path="data/assets/video/old.mp4",
        timeline_path="data/assets/video/old.json",
        total_duration_sec=12.0,
        quality_checks={"passed": True},
        voice_settings={"resolved_mock_mode": False},
    )


def _engine_result(output, success=False, summary="SAPI5 unavailable"):
    return EngineResult(
        engine_id="media",
        engine_version="1.0.0",
        run_id="worker-test",
        success=success,
        started_at="2026-01-01T00:00:00Z",
        ended_at="2026-01-01T00:00:01Z",
        summary=summary,
        errors=[] if success else [summary],
        outputs=[output] if output is not None else [],
    )


@pytest.mark.asyncio
async def test_worker_persists_failed_media_and_diagnostics_without_video():
    package = _package()
    session = _Session(package)
    job = SimpleNamespace(payload={"dry_run": False, "parameters": {"package_id": package.id}})
    result = _engine_result({
        "package_id": package.id,
        "status": "FAILED",
        "quality_report": {
            "passed": False,
            "production_eligible": False,
            "failed_stage": "voice",
            "issues": ["No installed English SAPI5 voice is available."],
        },
    })

    await StudioWorker()._persist_media_result(session, job, result)

    assert package.status == "FAILED"
    assert package.video_path is None
    assert package.timeline_path is None
    assert package.quality_checks["passed"] is False
    assert package.quality_checks["failed_stage"] == "voice"
    assert "No installed English SAPI5 voice" in package.quality_checks["issues"][0]
    assert session.commit_calls == 1


@pytest.mark.asyncio
async def test_worker_dry_run_does_not_mutate_media_package_to_ready():
    package = _package()
    session = _Session(package)
    job = SimpleNamespace(payload={"dry_run": True, "parameters": {"package_id": package.id}})
    result = _engine_result({"resolution": "1080x1920"}, success=True, summary="Simulated media run")

    await StudioWorker()._persist_media_result(session, job, result)

    assert package.status == "RENDERING"
    assert package.video_path == "data/assets/video/old.mp4"
    assert session.execute_calls == 0
    assert session.commit_calls == 0


@pytest.mark.asyncio
async def test_worker_empty_media_result_fails_closed_instead_of_ready():
    package = _package()
    session = _Session(package)
    job = SimpleNamespace(payload={"dry_run": False, "parameters": {"package_id": package.id}})

    await StudioWorker()._persist_media_result(
        session,
        job,
        _engine_result(None, success=True, summary="Unexpected empty engine result"),
    )

    assert package.status == "FAILED"
    assert package.video_path is None
    assert package.quality_checks["passed"] is False
    assert package.quality_checks["production_eligible"] is False
    assert session.commit_calls == 1
