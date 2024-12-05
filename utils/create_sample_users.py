# create_sample_users.py
import sys
import os
# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import User
from database import engine
from sqlalchemy.orm import sessionmaker
from utils.auth_utils import hash_password, verify_password
import bcrypt
import logging
from sqlalchemy import text

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_sample_users():
    # Create a session instance
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        logger.info("Starting user creation process...")
        
        # First, temporarily disable foreign key checks
        session.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        
        # Clear existing users
        logger.info("Clearing existing users...")
        session.execute(text("TRUNCATE TABLE users"))
        session.commit()
        
        # Re-enable foreign key checks
        session.execute(text("SET FOREIGN_KEY_CHECKS=1"))
        logger.info("Existing users cleared successfully")
        
        # Create admin and first-level users with proper password hashing
        users_to_create = [
            {
                "username": "admin",
                "password": "admin123",  # You should change this in production
                "firstname": "Admin",
                "lastname": "User",
                "email": "admin@example.com",
                "role": "admin",
                "is_admin": True
            },
            {
                "username": "first_level_user_1",
                "password": "password123",
                "firstname": "John",
                "lastname": "Doe",
                "email": "john@example.com",
                "role": "level_1",
                "is_admin": False
            },
            {
                "username": "first_level_user_2",
                "password": "password123",
                "firstname": "Jane",
                "lastname": "Smith",
                "email": "jane@example.com",
                "role": "level_1",
                "is_admin": False
            }
        ]
        
        created_users = []
        for user_data in users_to_create:
            try:
                logger.info(f"Creating user: {user_data['username']}")
                # Hash password using bcrypt
                hashed_password = hash_password(user_data["password"])
                logger.debug(f"Password hashed successfully for {user_data['username']}")
                
                user = User(
                    username=user_data["username"],
                    password=hashed_password,  # Store the hashed password
                    firstname=user_data["firstname"],
                    lastname=user_data["lastname"],
                    email=user_data["email"],
                    role=user_data["role"],
                    is_admin=user_data["is_admin"]
                )
                session.add(user)
                session.flush()  # Flush to get the ID without committing
                created_users.append(user)
                logger.info(f"User {user_data['username']} created successfully")
            except Exception as e:
                logger.error(f"Error creating user {user_data['username']}: {str(e)}")
                raise
        
        # Commit first-level users
        session.commit()
        logger.info("Admin and first-level users committed successfully")
        
        # Create second-level users
        second_level_users = [
            {
                "username": "second_level_user_1",
                "password": "password123",
                "firstname": "Alice",
                "lastname": "Brown",
                "email": "alice@example.com",
                "role": "level_2",
                "first_level_channel_id": created_users[1].id  # Adjusted index due to admin user
            },
            {
                "username": "second_level_user_2",
                "password": "password123",
                "firstname": "Bob",
                "lastname": "Green",
                "email": "bob@example.com",
                "role": "level_2",
                "first_level_channel_id": created_users[2].id  # Adjusted index due to admin user
            }
        ]
        
        for user_data in second_level_users:
            try:
                logger.info(f"Creating user: {user_data['username']}")
                # Hash password using bcrypt
                hashed_password = hash_password(user_data["password"])
                logger.debug(f"Password hashed successfully for {user_data['username']}")
                
                user = User(
                    username=user_data["username"],
                    password=hashed_password,  # Store the hashed password
                    firstname=user_data["firstname"],
                    lastname=user_data["lastname"],
                    email=user_data["email"],
                    role=user_data["role"],
                    first_level_channel_id=user_data["first_level_channel_id"],
                    is_admin=False
                )
                session.add(user)
                logger.info(f"User {user_data['username']} created successfully")
            except Exception as e:
                logger.error(f"Error creating user {user_data['username']}: {str(e)}")
                raise
        
        # Commit second-level users
        session.commit()
        logger.info("Second-level users committed successfully")
        
        # Verify passwords were stored correctly
        logger.info("Starting password verification...")
        for user_data in users_to_create + second_level_users:
            user = session.query(User).filter(User.username == user_data["username"]).first()
            try:
                # Print the actual stored hash for debugging
                logger.debug(f"Stored hash for {user.username}: {user.password}")
                
                if not verify_password(user_data["password"], user.password):
                    raise Exception(f"Password verification failed for user {user.username}")
                logger.info(f"Successfully verified password for user: {user.username}")
            except Exception as e:
                logger.error(f"Error verifying password for {user.username}: {str(e)}")
                raise

        logger.info("All users created and verified successfully!")

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        session.rollback()
        raise

    finally:
        session.close()
        logger.info("Database session closed")

if __name__ == "__main__":
    try:
        # Call this function to insert the sample users into the database
        create_sample_users()
    except Exception as e:
        logger.error(f"Failed to create sample users: {str(e)}")
        sys.exit(1)
