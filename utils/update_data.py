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
        # Update Tech-related companies to channel 1
        connection.execute(text("""
            UPDATE company_info 
            SET channel_id = 1 
            WHERE company_name LIKE '%Tech%' 
            OR company_name LIKE '%易安税联调测试企业%'
        """))
        
        # Update Finance-related companies to channel 2
        connection.execute(text("""
            UPDATE company_info 
            SET channel_id = 2 
            WHERE company_name LIKE '%Finance%' 
            AND channel_id = 0
        """))
        
        # Update remaining companies to channel 1 (as default)
        connection.execute(text("""
            UPDATE company_info 
            SET channel_id = 1 
            WHERE channel_id = 0
        """))
        
        # Update channel admins
        # Assign first_level_user_1 to Tech Channel
        connection.execute(text("""
            UPDATE channels 
            SET channel_admin_id = (
                SELECT id FROM users 
                WHERE username = 'first_level_user_1' 
                AND role = 'level_1' 
                LIMIT 1
            )
            WHERE id = 1
        """))
        
        # Assign first_level_user_2 to Finance Channel
        connection.execute(text("""
            UPDATE channels 
            SET channel_admin_id = (
                SELECT id FROM users 
                WHERE username = 'first_level_user_2' 
                AND role = 'level_1' 
                LIMIT 1
            )
            WHERE id = 2
        """))

print("Data update completed. Checking current state...")

# Verify the updates
with engine.connect() as connection:
    # Check channels and their admins
    result = connection.execute(text("""
        SELECT c.id, c.channel_name, c.channel_admin_id, u.username 
        FROM channels c 
        LEFT JOIN users u ON c.channel_admin_id = u.id
    """))
    print("\nChannels and Admins:")
    for row in result:
        print(f"Channel ID: {row[0]}, Name: {row[1]}, Admin ID: {row[2]}, Admin Username: {row[3]}")

    # Check company distribution
    result = connection.execute(text("""
        SELECT c.id, c.channel_name, COUNT(ci.id) as company_count 
        FROM channels c 
        LEFT JOIN company_info ci ON c.id = ci.channel_id 
        GROUP BY c.id, c.channel_name
    """))
    print("\nCompany Distribution:")
    for row in result:
        print(f"Channel ID: {row[0]}, Name: {row[1]}, Company Count: {row[2]}")
