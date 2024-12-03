from models import User
from database import session

def create_sample_users():
    # Create first-level users
    first_level_user_1 = User(
        username="first_level_user_1",
        password="password123",
        firstname="John",
        lastname="Doe",
        email="john@example.com",
        role="level_1",
        is_admin=False
    )
    
    first_level_user_2 = User(
        username="first_level_user_2",
        password="password123",
        firstname="Jane",
        lastname="Smith",
        email="jane@example.com",
        role="level_1",
        is_admin=False
    )
    
    # Create second-level users linked to first-level users
    second_level_user_1 = User(
        username="second_level_user_1",
        password="password123",
        firstname="Alice",
        lastname="Brown",
        email="alice@example.com",
        role="level_2",
        first_level_channel_id=first_level_user_1.id,  # Link to first-level user
        is_admin=False
    )
    
    second_level_user_2 = User(
        username="second_level_user_2",
        password="password123",
        firstname="Bob",
        lastname="Green",
        email="bob@example.com",
        role="level_2",
        first_level_channel_id=first_level_user_2.id,  # Link to first-level user
        is_admin=False
    )

    # Add users to the session and commit
    session.add(first_level_user_1)
    session.add(first_level_user_2)
    session.add(second_level_user_1)
    session.add(second_level_user_2)
    
    session.commit()

# Call this function to insert the sample users into the database
create_sample_users()
