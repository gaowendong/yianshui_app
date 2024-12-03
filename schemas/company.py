from pydantic import BaseModel

class CompanyInfoBase(BaseModel):
    company_name: str
    tax_number: str

class CompanyInfoCreate(CompanyInfoBase):
    pass

class CompanyInfoOut(CompanyInfoBase):
    id: int
    status: bool
    query_result: str | None = None

    class Config:
        orm_mode = True
