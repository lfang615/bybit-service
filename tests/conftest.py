import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient
import sys
from pathlib import Path
from ordermanager.app.main import app  
from dotenv import load_dotenv
import sys
from pathlib import Path

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
async def test_app() -> FastAPI:
    return app

@pytest.fixture
async def test_client(test_app: FastAPI) -> AsyncClient:
    async with TestClient(app=test_app, base_url="http://localhost:8000") as client:
        yield client
