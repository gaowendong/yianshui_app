import bcrypt
from fastapi import Request, HTTPException
from .token_utils import create_access_token, verify_access_token

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        print(f"Password verification error: {str(e)}")
        return False

def get_system_user_id_from_request(request: Request) -> int:
    """
    Extract system user ID from request headers
    """
    system_user_id = request.headers.get("X-System-User-Id")
    if not system_user_id:
        raise HTTPException(status_code=400, detail="System user ID not provided")
    try:
        return int(system_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid system user ID format")

def verify_user_ids(request_user_id: int, token_user_id: int) -> bool:
    """
    Verify that the user ID from the request matches the user ID from the token
    """
    try:
        return str(request_user_id) == str(token_user_id)
    except Exception as e:
        print(f"User ID verification error: {str(e)}")
        return False

__all__ = [
    'hash_password',
    'verify_password',
    'create_access_token',
    'verify_access_token',
    'get_system_user_id_from_request',
    'verify_user_ids'
]
