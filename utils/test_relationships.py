import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

# Database URL
DATABASE_URL = "mysql://root:password@localhost:3306/yianshui"

engine = create_engine(DATABASE_URL)

with engine.connect() as connection:
    # Test 1: Get channel info with admin details
    print("\nTest 1: Channel and Admin Details")
    result = connection.execute(text("""
        SELECT 
            c.id as channel_id,
            c.channel_name,
            u.username as admin_username,
            u.role as admin_role
        FROM channels c
        JOIN users u ON c.channel_admin_id = u.id
    """))
    for row in result:
        print(f"Channel: {row.channel_name}")
        print(f"Admin: {row.admin_username} (Role: {row.admin_role})")
        print("-" * 50)

    # Test 2: Get companies in each channel
    print("\nTest 2: Companies per Channel")
    result = connection.execute(text("""
        SELECT 
            c.channel_name,
            ci.company_name,
            u.username as admin_username
        FROM channels c
        JOIN company_info ci ON c.id = ci.channel_id
        JOIN users u ON c.channel_admin_id = u.id
        ORDER BY c.id, ci.id
        LIMIT 5
    """))
    for row in result:
        print(f"Channel: {row.channel_name}")
        print(f"Company: {row.company_name}")
        print(f"Channel Admin: {row.admin_username}")
        print("-" * 50)

    # Test 3: Count companies per channel
    print("\nTest 3: Company Count per Channel")
    result = connection.execute(text("""
        SELECT 
            c.channel_name,
            COUNT(ci.id) as company_count,
            u.username as admin_username
        FROM channels c
        LEFT JOIN company_info ci ON c.id = ci.channel_id
        JOIN users u ON c.channel_admin_id = u.id
        GROUP BY c.id, c.channel_name, u.username
    """))
    for row in result:
        print(f"Channel: {row.channel_name}")
        print(f"Number of Companies: {row.company_count}")
        print(f"Channel Admin: {row.admin_username}")
        print("-" * 50)
