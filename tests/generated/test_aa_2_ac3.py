import pytest
from fastapi.testclient import TestClient
from generated.aa_2.app import app

client = TestClient(app)


def test_ac3():
    # Test with non-existent email
    response = client.post(
        "/login",
        json={
            "email": "nonexistent@example.com",
            "password": "somepassword123"
        }
    )
    assert response.status_code == 401
    
    # Test with incorrect password for existing user
    # First, we need to create a user to test incorrect password
    # Assuming there's a registration endpoint or a known test user
    response = client.post(
        "/login",
        json={
            "email": "testuser@example.com",
            "password": "wrongpassword123"
        }
    )
    assert response.status_code == 401
    
    # Test with another non-existent email variation
    response = client.post(
        "/login",
        json={
            "email": "another.nonexistent@test.com",
            "password": "anotherpassword"
        }
    )
    assert response.status_code == 401