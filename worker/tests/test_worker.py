import pytest
from worker.worker import StudioWorker


@pytest.mark.asyncio
async def test_worker_initialization():
    worker = StudioWorker(poll_interval=0.1)
    assert worker.poll_interval == 0.1
    assert not worker._running
    worker.stop()
    assert not worker._running
