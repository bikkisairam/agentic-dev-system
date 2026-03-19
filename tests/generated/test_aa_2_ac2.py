import json
from datetime import datetime, timedelta
from unittest.mock import patch
import jwt
import pytest
from fastapi.testclient import TestClient
from generated.aa_2.app import app


client = TestClient(app)


def test_ac2():
    """Test that login returns 200 with JWT token on valid credentials"""
    
    mock_user = {
        "id": 1,
        "username": "testuser",
        "password": "hashed_password",
        "email": "test@example.com"
    }
    
    def mock_get_user_by_username(username):
        if username == "testuser":
            return mock_user
        return None
    
    def mock_verify_password(plain_password, hashed_password):
        return plain_password == "testpassword"
    
    with patch("generated.aa_2.app.get_user_by_username", side_effect=mock_get_user_by_username), \
         patch("generated.aa_2.app.verify_password", side_effect=mock_verify_password):
        
        response = client.post(
            "/login",
            json={"username": "testuser", "password": "testpassword"}
        )
    
    assert response.status_code == 200
    
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    
    token = data["access_token"]
    
    secret_key = "your-secret-key"
    algorithm = "HS256"
    
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
    except jwt.DecodeError:
        secret_key = "secret"
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
    
    assert "sub" in payload
    assert payload["sub"] == "testuser" or payload["sub"] == str(mock_user["id"])
    
    assert "exp" in payload
    exp_timestamp = payload["exp"]
    assert isinstance(exp_timestamp, (int, float))
    
    exp_time = datetime.fromtimestamp(exp_timestamp)
    current_time = datetime.utcnow()
    time_diff = (exp_time - current_time).total_seconds()
    
    assert 0 < time_diff <= 3600