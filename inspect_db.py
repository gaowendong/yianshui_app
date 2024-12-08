from sqlalchemy import create_engine, inspect

# MySQL connection URL
SQLALCHEMY_DATABASE_URL = "mysql://root:password@localhost:3306/yianshui"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
inspector = inspect(engine)

# Get columns for company_info table
columns = inspector.get_columns('company_info')
print("\nColumns in company_info table:")
for column in columns:
    print(f"- {column['name']}: {column['type']}")
