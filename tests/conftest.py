# Shared fixtures added here as tests are written
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from agentstatelib.api.app import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
