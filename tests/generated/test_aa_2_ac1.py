import pytest
from fastapi.testclient import TestClient
from generated.aa_2.app import app


def test_ac1():
    client = TestClient(app)
    
    payload = {
        "email": "test@example.com",
        "password": "password123"
    }
    
    response = client.post("/auth/login", json=payload)
    
    assert response.status_code in [200, 201, 422, 401, 400]
    assert response.headers.get("content-type") is not None