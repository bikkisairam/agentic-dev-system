import pytest
from fastapi.testclient import TestClient
from generated.aa_2.app import app


def test_ac3():
    client = TestClient(app)
    
    # Test with incorrect password
    response = client.post(
        "/login",
        json={
            "email": "user@example.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
    
    # Test with invalid email
    response = client.post(
        "/login",
        json={
            "email": "nonexistent@example.com",
            "password": "password123"
        }
    )
    assert response.status_code == 401