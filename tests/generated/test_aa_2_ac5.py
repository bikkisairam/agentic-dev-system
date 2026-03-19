from fastapi.testclient import TestClient
from generated.aa_2.app import app


def test_ac5():
    client = TestClient(app)
    
    # Send 5 requests from the same IP (should all succeed)
    for i in range(5):
        response = client.post("/login", json={"username": "test", "password": "test"})
        # First 5 requests should not return 429
        assert response.status_code != 429, f"Request {i+1} unexpectedly rate limited with status {response.status_code}"
    
    # Send 6th request from the same IP (should be rate limited)
    response = client.post("/login", json={"username": "test", "password": "test"})
    assert response.status_code == 429, f"Expected 429 Too Many Requests, got {response.status_code}"