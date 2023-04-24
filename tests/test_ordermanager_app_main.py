import pytest
from conftest import test_client

@pytest.mark.asyncio
async def test_root(test_client):
    response = await test_client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, World!"}
