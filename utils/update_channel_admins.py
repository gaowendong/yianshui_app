import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

# Database URL
DATABASE_URL = "mysql://root:password@localhost:3306/yianshui"

engine = create_engine(DATABASE_URL)

with engine.connect() as connection:
    # Start a transaction
    with connection.begin():
        # Update CH001 to be administered by first_level_user_1
        connection.execute(text("""
            UPDATE channels 
            SET channel_admin_id = (
                SELECT id FROM users 
                WHERE username = 'first_level_user_1' 
                AND role = 'level_1' 
                LIMIT 1
            )
            WHERE channel_number = 'CH001'
        """))
        
        # Update CH002 to be administered by first_level_user_2
        connection.execute(text("""
            UPDATE channels 
            SET channel_admin_id = (
                SELECT id FROM users 
                WHERE username = 'first_level_user_2' 
                AND role = 'level_1' 
                LIMIT 1
            )
            WHERE channel_number = 'CH002'
        """))

print("Channel admin updates completed. Checking current state...")

# Verify the updates
with engine.connect() as connection:
    result = connection.execute(text("""
        SELECT 
            c.channel_number,
            c.channel_name,
            u.username as admin_username,
            u.role as admin_role
        FROM channels c
        LEFT JOIN users u ON c.channel_admin_id = u.id
        ORDER BY c.channel_number
    """))
    print("\nChannel and Admin Details:")
    for row in result:
        print(f"Channel Number: {row.channel_number}")
        print(f"Channel Name: {row.channel_name}")
        print(f"Admin: {row.admin_username} (Role: {row.admin_role})")
        print("-" * 50)
