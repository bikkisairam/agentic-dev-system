import pytest
from fastapi.testclient import TestClient
from generated.aa_1.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_ac1(client):
    response = client.get("/health")
    assert response.status_code == 200