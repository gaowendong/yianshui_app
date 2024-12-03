from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Set up SQLite database connection (can replace with MySQL or PostgreSQL)
engine = create_engine(
    "mysql://root:password@localhost:3306/yianshui",
    pool_pre_ping=True,  # Enable connection health checks
    pool_recycle=3600,   # Recycle connections after 1 hour
    echo=True            # Log all SQL statements
)

# Base class for model definitions
Base = declarative_base()

# Create session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False  # Prevent expired object issues
)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {str(e)}")
        raise
    finally:
        db.close()
