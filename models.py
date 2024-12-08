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
    
    company_reports = relationship("CompanyReport", back_populates="user")

class CompanyInfo(Base):
    __tablename__ = 'company_info'
    
    id = Column(Integer, primary_key=True)
    company_name = Column(String(225), index=True)
    tax_number = Column(String(225), nullable=False)
    index_standard_type = Column(String(225))  # Added field for accounting standard
    industry = Column(String(225))  # Added field for industry type
    registration_type = Column(String(225))  # Added field for registration type
    taxpayer_nature = Column(String(225))  # Added field for taxpayer nature
    upload_year = Column(Integer)  # Added field for upload year
    uploaded_files = Column(JSON)  # Store array of file names as JSON
    post_data = Column(String(225))  # This can be JSON or stringified
    post_initiator_user_id = Column(Integer, ForeignKey('users.id'))
    status = Column(Boolean)  # Whether the post was successful
    query_result = Column(String(225), nullable=True)  # Store the query result
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # Added timestamp

    user = relationship("User")  # Removed back_populates since we removed the relationship from User
    company_reports = relationship("CompanyReport", back_populates="company_info", cascade="all, delete-orphan")

    # Add index for tax_number but remove unique constraint
    __table_args__ = (
        Index('ix_company_info_tax_number', 'tax_number'),
    )

class CompanyReport(Base):
    __tablename__ = "company_reports"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company_tax_number = Column(String(225), ForeignKey("company_info.tax_number", ondelete="CASCADE"), nullable=False)
    report_type = Column(String(50), nullable=False)  # 'annual', 'monthly', 'quarterly'
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=True)  # For monthly reports
    quarter = Column(Integer, nullable=True)  # For quarterly reports
    report_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="company_reports")
    company_info = relationship("CompanyInfo", back_populates="company_reports")
