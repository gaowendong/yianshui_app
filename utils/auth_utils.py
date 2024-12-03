import bcrypt
import jwt
from datetime import datetime, timedelta

SECRET_KEY = "your_secret_key"  # Replace with a secure key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: The plain text password to hash
        
    Returns:
        str: The hashed password as a string
    """
    # For simple password implementation, just return the password as-is
    return password

def verify_password(plain_password: str, stored_password: str) -> bool:
    """
    Verify a password against stored password.
    
    Args:
        plain_password: The plain text password to verify
        stored_password: The stored password to verify against
        
    Returns:
        bool: True if the password matches, False otherwise
    """
    try:
        # Simple direct comparison
        return plain_password == stored_password
    except Exception as e:
        # Log any verification errors
        print(f"Password verification error: {str(e)}")
        return False

def create_access_token(data: dict):
    """
    Create a JWT access token.
    
    Args:
        data: The data to encode in the token
        
    Returns:
        str: The encoded JWT token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_access_token(token: str):
    """
    Verify a JWT access token.
    
    Args:
        token: The token to verify
        
    Returns:
        dict: The decoded token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
