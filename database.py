from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Set up SQLite database connection (can replace with MySQL or PostgreSQL)
engine = create_engine("mysql://root:password@localhost:3306/yianshui", isolation_level='AUTOCOMMIT')

# Session for database interaction
session = sessionmaker(bind=engine)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for model definitions
Base = declarative_base()
