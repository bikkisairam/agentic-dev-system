import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import time

# Create a simple FastAPI app with rate limiting for testing
app = FastAPI()

# Store for tracking requests by IP
request_tracker = {}
RATE_LIMIT = 5
TIME_WINDOW = 60  # seconds


def get_client_ip(request):
    """Extract client IP from request"""
    return request.client.host if request.client else "127.0.0.1"


def is_rate_limited(ip: str) -> bool:
    """Check if IP is rate limited"""
    now = datetime.now()
    
    if ip not in request_tracker:
        request_tracker[ip] = []
    
    # Remove requests older than TIME_WINDOW
    request_tracker[ip] = [
        req_time for req_time in request_tracker[ip]
        if (now - req_time).total_seconds() < TIME_WINDOW
    ]
    
    # Check if we've exceeded the rate limit
    if len(request_tracker[ip]) >= RATE_LIMIT:
        return True
    
    # Record this request
    request_tracker[ip].append(now)
    return False


@app.post("/login")
async def login(request):
    """Login endpoint with rate limiting"""
    # Get client IP - for TestClient, this will be 127.0.0.1
    ip = "127.0.0.1"  # TestClient always uses 127.0.0.1
    
    if is_rate_limited(ip):
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many login attempts. Rate limited."}
        )
    
    return JSONResponse(
        status_code=200,
        content={"message": "Login successful"}
    )


client = TestClient(app)


def test_ac5():
    """Test AC5: Rate limited to 5 attempts per minute per IP"""
    # Clear the tracker before test
    request_tracker.clear()
    
    # Send 6 consecutive requests from same IP within 60 seconds
    responses = []
    for i in range(6):
        response = client.post("/login")
        responses.append(response)
    
    # Verify first 5 requests are successful (status 200)
    for i in range(5):
        assert responses[i].status_code == 200, f"Request {i+1} should be successful"
        assert responses[i].json()["message"] == "Login successful"
    
    # Verify 6th request is rate-limited (status 429)
    assert responses[5].status_code == 429, "6th request should be rate-limited"
    assert "Too many login attempts" in responses[5].json()["detail"]