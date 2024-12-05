from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON, UniqueConstraint, Index
from database import Base, engine
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(225))
    username = Column(String(225))
    password = Column(String(225))
    firstname = Column(String(225))
    lastname = Column(String(225))
    is_admin = Column(Boolean)
    role = Column(String(225))  # "level_1" for first-level, "level_2" for second-level
    first_level_channel_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    companies = relationship("CompanyInfo", back_populates="user")
    query_results = relationship("QueryResult", back_populates="user")
    risk_reports = relationship("RiskReport", back_populates="user")
    company_reports = relationship("CompanyReport", back_populates="user")

class CompanyInfo(Base):
    __tablename__ = 'company_info'
    
    id = Column(Integer, primary_key=True)
    company_name = Column(String(225), index=True)
    tax_number = Column(String(225), nullable=False)
    post_data = Column(String(225))  # This can be JSON or stringified
    post_initiator_user_id = Column(Integer, ForeignKey('users.id'))
    status = Column(Boolean)  # Whether the post was successful
    query_result = Column(String(225), nullable=True)  # Store the query result

    user = relationship("User", back_populates="companies")
    query_results = relationship("QueryResult", back_populates="company_info")
    company_reports = relationship("CompanyReport", back_populates="company_info")

    # Add index for tax_number but remove unique constraint
    __table_args__ = (
        Index('ix_company_info_tax_number', 'tax_number'),
    )

class QueryResult(Base):
    __tablename__ = 'query_results'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    company_info_id = Column(Integer, ForeignKey("company_info.id"))
    query_data = Column(String(1000))  # Increased length for query data
    created_at = Column(String(225))

    user = relationship("User", back_populates="query_results")
    company_info = relationship("CompanyInfo", back_populates="query_results")

class RiskReport(Base):
    __tablename__ = "risk_reports"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    response_data = Column(JSON)  # Store the entire JSON response
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="risk_reports")

class CompanyReport(Base):
    __tablename__ = "company_reports"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company_tax_number = Column(String(225), ForeignKey("company_info.tax_number"), nullable=False)
    report_type = Column(String(50), nullable=False)  # 'annual', 'monthly', 'quarterly'
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=True)  # For monthly reports
    quarter = Column(Integer, nullable=True)  # For quarterly reports
    report_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="company_reports")
    company_info = relationship("CompanyInfo", back_populates="company_reports")
