from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from database import Base, engine, session
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(225))
    username = Column(String(225))
    password = Column(String(225))
    firstname = Column(String(225))
    lastname = Column(String(225))
    is_admin = Column(Boolean)
    # 'role' indicates if the user is a first-level or second-level channel
    role = Column(String(225))  # "level_1" for first-level, "level_2" for second-level
    first_level_channel_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # # Relationship to link second-level users to their first-level counterpart
    # first_level_channel = relationship("User", remote_side=[id])
    companies = relationship("CompanyInfo", back_populates="user")
    query_results = relationship("QueryResult", back_populates="user")

class CompanyInfo(Base):
    __tablename__ = 'company_info'
    
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(225), index=True)
    tax_number = Column(String(225))
    post_data = Column(String(225))  # This can be JSON or stringified
    post_initiator_user_id = Column(Integer, ForeignKey('users.id'))
    status = Column(Boolean)  # Whether the post was successful
    query_result = Column(String(225), nullable=True)  # Store the query result

    user = relationship("User", back_populates="companies")
    query_results = relationship("QueryResult", back_populates="company_info")

class QueryResult(Base):
    __tablename__ = 'query_results'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    company_info_id = Column(Integer, ForeignKey("company_info.id"))
    query_data = Column(String(1000))  # Increased length for query data
    created_at = Column(String(225))

    user = relationship("User", back_populates="query_results")
    company_info = relationship("CompanyInfo", back_populates="query_results")

# Create tables in the database
Base.metadata.create_all(engine)
