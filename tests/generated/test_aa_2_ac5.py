import pytest
from fastapi.testclient import TestClient
from generated.aa_2.app import app


def test_ac5():
    """Test AC5: Rate limited to 5 attempts per minute per IP"""
    client = TestClient(app)
    
    # Send 6 requests from the same IP within 60 seconds
    responses = []
    for i in range(6):
        response = client.post(
            "/login",
            json={"username": "testuser", "password": "wrongpassword"},
            headers={"X-Forwarded-For": "192.168.1.1"}
        )
        responses.append(response)
    
    # First 5 requests should succeed (or at least not be rate limited)
    for i in range(5):
        assert responses[i].status_code != 429, f"Request {i+1} should not be rate limited"
    
    # 6th request should return rate limit error (429 Too Many Requests)
    assert responses[5].status_code == 429, "6th request should be rate limited"