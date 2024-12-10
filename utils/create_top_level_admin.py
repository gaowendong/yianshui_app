import os
import sys

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import User
from utils.auth_utils import hash_password

def create_top_level_admin(username: str, password: str, email: str):
    """Create a new top level administrator user"""
    db = SessionLocal()
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            print(f"User {username} already exists")
            return

        # Create new top level admin user
        hashed_password = hash_password(password)
        new_user = User(
            username=username,
            password=hashed_password,
            email=email,
            is_admin=True,
            is_top_level_admin=True,
            role="top_level_admin"
        )
        
        db.add(new_user)
        db.commit()
        print(f"Successfully created top level admin user: {username}")
        
    except Exception as e:
        print(f"Error creating top level admin: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python create_top_level_admin.py <username> <password> <email>")
        sys.exit(1)
    
    username = sys.argv[1] #topadmin 
    password = sys.argv[2] #admin123 
    email = sys.argv[3]
    
    create_top_level_admin(username, password, email)
