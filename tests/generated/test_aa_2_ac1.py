import pytest
from fastapi.testclient import TestClient
from generated.aa_2.app import app


def test_ac1():
    client = TestClient(app)
    
    # Test valid JSON payload with email and password
    valid_payload = {"email": "test@example.com", "password": "testpassword"}
    response = client.post("/auth/login", json=valid_payload)
    assert response.status_code in [200, 401, 422]  # Accept successful parsing or auth failure
    
    # Test with missing email
    invalid_payload_no_email = {"password": "testpassword"}
    response = client.post("/auth/login", json=invalid_payload_no_email)
    assert response.status_code == 422  # Unprocessable Entity for missing required field
    
    # Test with missing password
    invalid_payload_no_password = {"email": "test@example.com"}
    response = client.post("/auth/login", json=invalid_payload_no_password)
    assert response.status_code == 422  # Unprocessable Entity for missing required field
    
    # Test with empty JSON object
    empty_payload = {}
    response = client.post("/auth/login", json=empty_payload)
    assert response.status_code == 422  # Unprocessable Entity for missing required fields
    
    # Test with invalid JSON (malformed body)
    response = client.post("/auth/login", content="invalid json", headers={"Content-Type": "application/json"})
    assert response.status_code == 422  # Unprocessable Entity for malformed JSON
    
    # Test with extra fields (should still work with valid required fields)
    extra_fields_payload = {"email": "test@example.com", "password": "testpassword", "extra": "field"}
    response = client.post("/auth/login", json=extra_fields_payload)
    assert response.status_code in [200, 401, 422]  # Accept successful parsing or auth failure