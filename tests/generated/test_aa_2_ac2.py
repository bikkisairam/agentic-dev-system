import pytest
from fastapi.testclient import TestClient
from generated.aa_2.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_ac2(client):
    """Test that login with valid credentials returns 200 with JWT token"""
    # Test with known valid credentials
    valid_credentials = {
        "username": "testuser",
        "password": "testpassword"
    }
    
    response = client.post("/login", json=valid_credentials)
    
    # Assert 200 status code
    assert response.status_code == 200
    
    # Assert token is in response body
    assert "token" in response.json()
    assert response.json()["token"] is not None
    assert isinstance(response.json()["token"], str)
    assert len(response.json()["token"]) > 0