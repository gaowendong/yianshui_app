import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException

# Secret key for JWT tokens - should be moved to environment variables in production
SECRET_KEY = "your-super-secret-key-2023"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict):
    """
    Create a new JWT access token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_access_token(token: str) -> dict:
    """
    Verify a JWT access token and return its payload
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except (jwt.InvalidTokenError, jwt.DecodeError):  # Using correct PyJWT exceptions
        raise HTTPException(status_code=401, detail="Could not validate token")
