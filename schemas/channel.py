from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ChannelBase(BaseModel):
    channel_number: str
    channel_name: str
    channel_location: Optional[str] = None
    industry: Optional[str] = None
    contact_person: Optional[str] = None
    contact_number: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    app: Optional[str] = None
    official_account: Optional[str] = None
    douyin_account: Optional[str] = None
    balance: float = Field(default=0.0, description="Channel's pre-deposited balance")

class ChannelCreate(ChannelBase):
    pass

class Channel(ChannelBase):
    id: int
    registration_time: datetime

    class Config:
        orm_mode = True

class ChannelResponse(Channel):
    """
    Response model for channel operations
    """
    pass

class TransactionBase(BaseModel):
    channel_id: int
    report_id: int
    transaction_type: str = Field(..., description="Either 'upload' or 'download'")
    cost: float

class TransactionCreate(TransactionBase):
    user_id: int

class Transaction(TransactionBase):
    id: int
    created_at: datetime
    
    class Config:
        orm_mode = True

class DepositRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount to deposit into channel balance")

class BalanceResponse(BaseModel):
    channel_id: int
    current_balance: float
    last_updated: datetime

class ChannelDashboardData(BaseModel):
    """
    Data model for channel dashboard
    """
    channel: Channel
    total_uploads: int
    total_downloads: int
    total_cost: float
    recent_transactions: list[Transaction]
