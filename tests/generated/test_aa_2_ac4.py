import time
import jwt
import pytest
from fastapi.testclient import TestClient
from generated.aa_2.app import app

client = TestClient(app)


def test_ac4():
    """Test that JWT expires in 24 hours"""
    # Login to get JWT token
    response = client.post(
        "/login",
        json={"username": "testuser", "password": "testpass"}
    )
    
    assert response.status_code == 200
    token = response.json()["access_token"]
    
    # Decode JWT token without verification to get exp claim
    decoded = jwt.decode(token, options={"verify_signature": False})
    
    # Get current time and exp time
    current_time = time.time()
    exp_time = decoded["exp"]
    
    # Calculate difference in seconds
    time_diff = exp_time - current_time
    
    # 24 hours = 86400 seconds
    # Allow 5 second tolerance for test execution time
    expected_expiry = 24 * 60 * 60  # 86400 seconds
    tolerance = 5
    
    assert abs(time_diff - expected_expiry) <= tolerance, \
        f"Token expiry time {time_diff}s is not approximately 24 hours ({expected_expiry}s)"