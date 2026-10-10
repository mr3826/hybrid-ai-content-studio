import sqlite3

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.core.database import engine, AsyncSessionLocal
from app.models.base import Base


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    from app.engines.catalog import register_all_catalog_engines
    register_all_catalog_engines()
    yield
    # Keep database tables for inspection or teardown


@pytest_asyncio.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.fixture
def isolated_backup_workspace(monkeypatch, tmp_path):
    """Give backup API tests a private file-backed SQLite source, never the developer database."""
    from app.engines.core.registry import engine_registry

    cleanup_engine = engine_registry.get("cleanup")
    assert cleanup_engine is not None
    manager = cleanup_engine.backup_manager
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(manager, "workspace_root", tmp_path)
    monkeypatch.setattr(manager, "backup_dir", backup_dir)

    db_path = tmp_path / "data" / "db" / "studio.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE backup_fixture (id INTEGER PRIMARY KEY)")


@pytest.fixture(autouse=True)
def enforce_test_isolation():
    """Keep provider calls isolated and mark deterministic test narration as mock output."""
    from app.core.config import settings
    prev_mode = settings.AI_MOCK_MODE
    prev_tts_mode = settings.TTS_MOCK_MODE
    settings.AI_MOCK_MODE = True
    settings.TTS_MOCK_MODE = True
    yield
    settings.AI_MOCK_MODE = prev_mode
    settings.TTS_MOCK_MODE = prev_tts_mode
