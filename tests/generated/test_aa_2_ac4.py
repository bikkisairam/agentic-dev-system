import pytest
import jwt
from datetime import datetime, timedelta
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
    
    # Decode JWT without verification to get the claims
    decoded = jwt.decode(token, options={"verify_signature": False})
    
    # Get the exp claim
    exp_timestamp = decoded["exp"]
    
    # Get current timestamp
    current_timestamp = datetime.utcnow().timestamp()
    
    # Calculate expected expiration (24 hours from now)
    expected_exp = current_timestamp + (24 * 60 * 60)
    
    # Allow 5 second tolerance for test execution time
    tolerance = 5
    assert abs(exp_timestamp - expected_exp) <= tolerance, \
        f"Token expiration {exp_timestamp} is not 24 hours from now {expected_exp}"