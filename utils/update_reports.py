import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import engine

def update_reports():
    with engine.connect() as connection:
        # Create the update query with correct table name
        update_query = text("""
            UPDATE company_reports 
            SET processed_by_user_id = 4 
            WHERE processed_by_user_id = 0
        """)
        
        # Execute the query
        result = connection.execute(update_query)
        connection.commit()
        
        return result.rowcount

if __name__ == "__main__":
    rows_updated = update_reports()
    print(f"Updated {rows_updated} reports")
