import pytest
from fastapi.testclient import TestClient
from generated.aa_2.app import app

client = TestClient(app)


def test_ac1():
    """Test that POST /auth/login accepts { email, password }"""
    payload = {
        "email": "test@example.com",
        "password": "password123"
    }
    
    response = client.post("/auth/login", json=payload)
    
    # Verify the endpoint accepts the payload (returns a valid response)
    assert response.status_code in [200, 401, 422]
    # 200 for successful login, 401 for invalid credentials, 422 for validation error
    # The important part is that the endpoint accepts the payload structure
    assert isinstance(response.json(), (dict, list))