from fastapi.testclient import TestClient
from generated.aa_1.app import app


def test_ac1():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200