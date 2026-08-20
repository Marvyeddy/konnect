import pytest


@pytest.mark.asyncio
async def test_root(client):
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["message"] == "Welcome to the konnect app"
