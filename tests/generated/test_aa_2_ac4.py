import jwt
import time
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from generated.aa_2.app import app

def test_ac4():
    client = TestClient(app)
    
    response = client.post("/login", json={"username": "testuser", "password": "testpass"})
    
    assert response.status_code == 200
    token = response.json()["access_token"]
    
    decoded_token = jwt.decode(token, options={"verify_signature": False})
    
    exp_timestamp = decoded_token["exp"]
    iat_timestamp = decoded_token["iat"]
    
    time_diff = exp_timestamp - iat_timestamp
    
    expected_24_hours_in_seconds = 24 * 60 * 60
    assert time_diff == expected_24_hours_in_seconds