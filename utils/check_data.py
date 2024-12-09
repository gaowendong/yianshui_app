import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

# Database URL
DATABASE_URL = "mysql://root:password@localhost:3306/yianshui"

engine = create_engine(DATABASE_URL)

with engine.connect() as connection:
    # Check channels
    result = connection.execute(text("SELECT id, channel_name FROM channels"))
    print("\nChannels:")
    for row in result:
        print(f"ID: {row[0]}, Name: {row[1]}")

    # Check company_info channel_ids
    result = connection.execute(text("SELECT id, company_name, channel_id FROM company_info"))
    print("\nCompany Info:")
    for row in result:
        print(f"ID: {row[0]}, Name: {row[1]}, Channel ID: {row[2]}")

    # Check users who are level1
    result = connection.execute(text("SELECT id, username, role FROM users WHERE role = 'level_1'"))
    print("\nLevel 1 Users:")
    for row in result:
        print(f"ID: {row[0]}, Username: {row[1]}, Role: {row[2]}")
