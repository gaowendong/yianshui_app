from sqlalchemy import create_engine

# Replace with your actual connection string
engine = create_engine('mysql+mysqldb://root:password@localhost:3306/yianshui')

# Test connection
try:
    with engine.connect() as connection:
        print("Connection successful")
except Exception as e:
    print(f"Connection failed: {e}")