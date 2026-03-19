from fastapi import FastAPI, status, HTTPException, Request
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from typing import Optional, Dict
from collections import defaultdict
import jwt
import bcrypt
import time

app = FastAPI()


class LoginRequest(BaseModel):
    email: EmailStr
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
        "hashed_password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5YmMxSUaqvyMa"
    }
}

rate_limit_store: Dict[str, list] = defaultdict(list)


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    if request.client:
        return request.client.host
    return "unknown"


def check_rate_limit(ip: str) -> bool:
    """
    Check if IP has exceeded rate limit using sliding window approach.
    
    Returns True if request is allowed, False if rate limited.
    """
    current_time = time.time()
    window_start = current_time - RATE_LIMIT_WINDOW_SECONDS

    rate_limit_store[ip] = [
        timestamp for timestamp in rate_limit_store[ip]
        if timestamp > window_start
    ]

    if len(rate_limit_store[ip]) >= RATE_LIMIT_ATTEMPTS:
        return False

    rate_limit_store[ip].append(current_time)
    return True


def create_access_token(
    data: dict, expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(seconds=ACCESS_TOKEN_EXPIRE_SECONDS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hashed password."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


@app.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest, http_request: Request) -> LoginResponse:
    """Handle user login with rate limiting."""
    client_ip = get_client_ip(http_request)

    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )

    user = USERS_DB.get(request.email)

    if user is None or not verify_password(
        request.password, user["hashed_password"]
    ):
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