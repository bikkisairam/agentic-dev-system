import pytest
from fastapi.testclient import TestClient
from generated.aa_2.app import app


def test_ac2():
    """Test that valid credentials return 200 with JWT token"""
    client = TestClient(app)
    
    # Valid credentials for login
    valid_credentials = {
        "email": "user@example.com",
        "password": "password123"
    }
    
    # Make login request
    response = client.post("/login", json=valid_credentials)
    
    # Assert response code is 200
    assert response.status_code == 200
    
    # Assert response contains a token
    response_data = response.json()
    assert "token" in response_data
    assert response_data["token"] is not None
    assert isinstance(response_data["token"], str)
    assert len(response_data["token"]) > 0
    
    # Validate JWT token format (should have 3 parts separated by dots)
    token = response_data["token"]
    assert token.count(".") == 2  # JWT tokens have format: header.payload.signature