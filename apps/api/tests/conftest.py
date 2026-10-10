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


@pytest.fixture(autouse=True)
def enforce_test_isolation():
    """Guarantee automated tests never make live AI provider calls and remain strictly isolated."""
    from app.core.config import settings
    prev_mode = settings.AI_MOCK_MODE
    settings.AI_MOCK_MODE = True
    yield
    settings.AI_MOCK_MODE = prev_mode

