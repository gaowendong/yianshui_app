from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON, Float, UniqueConstraint, Index
from database import Base, engine
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True)
    channel_number = Column(String(50), unique=True, nullable=False)
    channel_name = Column(String(225), nullable=False)
    channel_location = Column(String(225), nullable=True)
    industry = Column(String(225), nullable=True)
    contact_person = Column(String(225), nullable=True)
    contact_number = Column(String(50), nullable=True)
    email = Column(String(225), nullable=True)
    registration_time = Column(DateTime(timezone=True), server_default=func.now())
    website = Column(String(225), nullable=True)
    app = Column(String(225), nullable=True)
    official_account = Column(String(225), nullable=True)
    douyin_account = Column(String(225), nullable=True)
    balance = Column(Float, default=0.0)  # Pre-deposited money
    channel_admin_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    # Relationships
    users = relationship("User", back_populates="channel", foreign_keys="[User.channel_id]")
    channel_admin = relationship("User", foreign_keys=[channel_admin_id])
    report_transactions = relationship("ReportTransaction", back_populates="channel", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(225))
    username = Column(String(225))
    password = Column(String(225))
    firstname = Column(String(225))
    lastname = Column(String(225))
    is_admin = Column(Boolean)
    is_top_level_admin = Column(Boolean, default=False)  # Added field for top level admin
    role = Column(String(225))  # "level_1" for first-level, "level_2" for second-level, "top_level_admin" for top admin
    first_level_channel_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=True)
    
    # Relationships
    company_reports = relationship("CompanyReport", back_populates="processed_by_user", cascade="all, delete-orphan")
    channel = relationship("Channel", back_populates="users", foreign_keys=[channel_id])
    administered_channels = relationship("Channel", foreign_keys=[Channel.channel_admin_id], back_populates="channel_admin")
    report_transactions = relationship("ReportTransaction", back_populates="user", cascade="all, delete-orphan")

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
    post_initiator_user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    status = Column(Boolean)  # Whether the post was successful
    query_result = Column(String(225), nullable=True)  # Store the query result
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # Added timestamp

    user = relationship("User")
    company_reports = relationship("CompanyReport", back_populates="company_info", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_company_info_tax_number', 'tax_number'),
    )

class CompanyReport(Base):
    __tablename__ = "company_reports"

    id = Column(Integer, primary_key=True)
    processed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    company_tax_number = Column(String(225), ForeignKey("company_info.tax_number", ondelete="CASCADE"), nullable=False)
    report_type = Column(String(50), nullable=False)  # 'annual', 'monthly', 'quarterly'
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=True)  # For monthly reports
    quarter = Column(Integer, nullable=True)  # For quarterly reports
    report_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    processed_by_user = relationship("User", back_populates="company_reports")
    company_info = relationship("CompanyInfo", back_populates="company_reports")

class ReportTransaction(Base):
    __tablename__ = "report_transactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    report_id = Column(Integer, ForeignKey("company_reports.id", ondelete="CASCADE"), nullable=False)
    transaction_type = Column(String(50), nullable=False)  # "upload" or "download"
    cost = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="report_transactions")
    channel = relationship("Channel", back_populates="report_transactions")
    report = relationship("CompanyReport")
