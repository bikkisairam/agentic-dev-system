import os
import sys
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
import jwt
from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str


SECRET_KEY = "your-secret-key-change-this"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 86400
RATE_LIMIT_ATTEMPTS = 5
RATE_LIMIT_WINDOW_SECONDS = 60

USERS_DB = {
    "test@example.com": {
        "email": "test@example.com",
        "hashed_password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5YmMxSUaqvyMa",
    }
}

rate_limit_store: dict[str, list[float]] = {}


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    return request.client.host if request.client else "unknown"


def check_rate_limit(ip: str) -> bool:
    """Check if IP has exceeded rate limit using sliding window approach.

    Returns True if request is allowed, False if rate limited.
    """
    if ip not in rate_limit_store:
        rate_limit_store[ip] = []

    current_time = __import__("time").time()
    window_start = current_time - RATE_LIMIT_WINDOW_SECONDS

    rate_limit_store[ip] = [
        timestamp
        for timestamp in rate_limit_store[ip]
        if timestamp > window_start
    ]

    if len(rate_limit_store[ip]) >= RATE_LIMIT_ATTEMPTS:
        return False

    rate_limit_store[ip].append(current_time)
    return True


def create_access_token(
    data: dict, expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token with 24-hour expiration.

    Sets JWT exp claim to current time plus 86400 seconds (24 hours).
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(seconds=ACCESS_TOKEN_EXPIRE_SECONDS)
    to_encode.update({"exp": int(expire.timestamp())})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hashed password."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def authenticate_user(email: str, password: str) -> bool:
    """Authenticate user by email and password.

    Returns False if email not found or password verification fails.
    """
    user = USERS_DB.get(email)
    if user is None:
        return False
    return verify_password(password, user["hashed_password"])


app = FastAPI()


@app.post(
    "/auth/login", response_model=LoginResponse, status_code=status.HTTP_200_OK
)
async def login(request: LoginRequest, http_request: Request) -> LoginResponse:
    """Handle user login with rate limiting and JWT token generation.

    Returns 200 with JWT token on valid credentials.
    Returns 401 Unauthorized when email not found or password verification fails.
    Returns 429 Too Many Requests when rate limit exceeded (5 attempts per minute per IP).
    Queries database for user by email, verifies password with bcrypt,
    generates JWT token with 24-hour expiration (86400 seconds).
    """
    client_ip = get_client_ip(http_request)

    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )

    if not authenticate_user(request.email, request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    access_token_expires = timedelta(seconds=ACCESS_TOKEN_EXPIRE_SECONDS)
    access_token = create_access_token(
        data={"sub": request.email}, expires_delta=access_token_expires
    )
    return LoginResponse(access_token=access_token, token_type="bearer")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)