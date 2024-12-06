import bcrypt
import jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db
from services.auth import get_cached_token

SECRET_KEY = "your_secret_key"  # Replace with a secure key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: The plain text password to hash
        
    Returns:
        str: The hashed password as a string
    """
    # Convert the password to bytes
    password_bytes = password.encode('utf-8')
    # Generate a salt and hash the password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    # Return the hashed password as a string
    return hashed.decode('utf-8')

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
        # Convert passwords to bytes for bcrypt
        plain_password_bytes = plain_password.encode('utf-8')
        stored_password_bytes = stored_password.encode('utf-8')
        # Use bcrypt to verify the password
        return bcrypt.checkpw(plain_password_bytes, stored_password_bytes)
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

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Get the current authenticated user.
    
    Args:
        token: The JWT token from the request
        db: The database session
        
    Returns:
        User: The current authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    from models import User  # Import here to avoid circular imports
    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    return user

async def verify_user_ids(system_user_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Verify both system user ID and database user ID.
    
    Args:
        system_user_id: The Yi'an system user ID
        request: The FastAPI request object
        db: The database session
        
    Returns:
        tuple: (database_user_id, database_user)
        
    Raises:
        HTTPException: If either ID is invalid or authentication fails
    """
    # First verify the database user from the Authorization token
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = auth_header.split(' ')[1]
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    database_user_id = payload.get("user_id")
    if not database_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in token"
        )
    
    # Verify database user exists
    from models import User  # Import here to avoid circular imports
    database_user = db.query(User).filter(User.id == database_user_id).first()
    if not database_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {database_user_id} not found in database"
        )
    
    # Verify Yi'an system token exists
    yian_token = get_cached_token(system_user_id)
    if not yian_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yi'an system authentication token not found. Please login to Yi'an system first."
        )
    
    return database_user_id, database_user

async def get_system_user_id_from_request(request: Request, db: Session = Depends(get_db)) -> int:
    """
    Extract and verify the database user ID from the request.
    
    Args:
        request: The FastAPI request object
        db: The database session
        
    Returns:
        int: The verified database user ID
        
    Raises:
        HTTPException: If authentication fails or user ID is invalid
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = auth_header.split(' ')[1]
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in token"
        )
    
    # Verify user exists in database
    from models import User  # Import here to avoid circular imports
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found in database"
        )
    
    return user_id
