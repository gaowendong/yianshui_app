from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Annotated, List
from datetime import datetime
from pydantic import BaseModel
import json
import traceback

from database import SessionLocal
from models import User, CompanyInfo, CompanyReport
from services.company import upload_company_info_batch, query_third_party_system
from services.auth import check_redis_connection, redis_client, get_cached_token, register_tenant
from utils.auth_utils import verify_user_ids, verify_access_token

# Initialize router for API routes
api_router = APIRouter(prefix="/api/v1", tags=["company_info"])

# Initialize router for page routes
page_router = APIRouter(tags=["pages"])

# Initialize templates
templates = Jinja2Templates(directory="templates")

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@page_router.get("/upload_base_info", response_class=HTMLResponse)
async def upload_base_info_page(request: Request):
    """Render upload base info page"""
    return templates.TemplateResponse("upload_base_info.html", {"request": request})

@page_router.get("/upload_company_info", response_class=HTMLResponse)
async def upload_company_info_page(request: Request):
    """Render upload company info page"""
    return templates.TemplateResponse("upload_company_info.html", {"request": request})

@page_router.get("/download-report", response_class=HTMLResponse)
async def download_report_page(request: Request):
    """Render download report page"""
    return templates.TemplateResponse("download_report.html", {"request": request})

@api_router.get("/test-redis")
async def test_redis():
    """Test Redis connection"""
    try:
        check_redis_connection()
        return {"status": "success", "message": "Redis connection successful"}
    except HTTPException as e:
        return {"status": "error", "message": str(e.detail)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class CompanyRegistration(BaseModel):
    """Schema for company registration"""
    companyName: str
    indexStandardType: str
    industry: str
    registrationType: str
    taxpayerNature: str
    taxpayerNo: str

@api_router.post("/register")
async def register_company(
    company_data: CompanyRegistration,
    request: Request,
    db: Session = Depends(get_db)
):
    """Register a new company"""
    try:
        # Get user ID from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid token")
        
        token = auth_header.split(" ")[1]
        payload = verify_access_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Register with Yi'an Tax system
        registration_data = {
            "companyName": company_data.companyName,
            "indexStandardType": int(company_data.indexStandardType),
            "industry": int(company_data.industry),
            "registrationType": int(company_data.registrationType),
            "taxpayerNature": int(company_data.taxpayerNature),
            "taxpayerNo": company_data.taxpayerNo,
            "userId": user_id
        }
        
        result = await register_tenant(registration_data)
        return {"status": 200, "data": result}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class DownloadReportRequest(BaseModel):
    """Schema for download report request"""
    dateSource: int
    dateTime: str
    dateType: int
    year: int
    reportType: str
    month: int = None
    quarter: int = None

@api_router.post("/download-report/{system_user_id}")
async def download_report(
    system_user_id: int,
    report_data: DownloadReportRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Download report for a specific system user"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid token")
        
        token = auth_header.split(" ")[1]
        payload = verify_access_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Get user from database
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get token from Redis
        token = None
        for key in redis_client.scan_iter("yas_token:*"):
            token_data = redis_client.get(key)
            if token_data:
                try:
                    data = json.loads(token_data)
                    if str(data.get('systemUserId')) == str(system_user_id):
                        token = data.get('token')
                        break
                except json.JSONDecodeError:
                    continue

        if not token:
            raise HTTPException(status_code=401, detail="Token not found. Please login first.")

        # Query third party system
        result = await query_third_party_system(
            db=db,
            date_source=report_data.dateSource,
            date_time=report_data.dateTime,
            date_type=report_data.dateType,
            year=report_data.year,
            token=token,
            current_user=user,
            report_type=report_data.reportType
        )
        return result

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class StoreReportRequest(BaseModel):
    """Schema for storing report"""
    user_id: int
    company_tax_number: str
    report_type: str
    year: int
    month: int = None
    quarter: int = None
    report_data: dict

@api_router.post("/store-report")
async def store_report(
    report_data: StoreReportRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Store a report in the database"""
    try:
        # Get the system user ID and tax number
        system_user_id = report_data.user_id
        tax_number = report_data.company_tax_number
        
        # First, try to find an existing user by checking CompanyInfo records
        company_info = db.query(CompanyInfo).filter(
            CompanyInfo.tax_number == tax_number
        ).first()
        
        if company_info and company_info.post_initiator_user_id:
            actual_user = db.query(User).filter(
                User.id == company_info.post_initiator_user_id
            ).first()
        else:
            # If no existing user found, find any admin user to associate with
            actual_user = db.query(User).filter(
                User.is_admin == True
            ).first()
            
            if not actual_user:
                # If no admin user exists, create a new system user
                actual_user = User(
                    username=f"system_user_{system_user_id}",
                    email=f"system_{system_user_id}@system.local",
                    password="",  # No password needed for system user
                    is_admin=False,
                    role="system"
                )
                db.add(actual_user)
                db.commit()
                db.refresh(actual_user)

        # Validate report type
        valid_report_types = ['annual', 'monthly', 'quarterly']
        if report_data.report_type not in valid_report_types:
            raise HTTPException(status_code=400, detail="Invalid report type")

        # Validate month/quarter based on report type
        if report_data.report_type == 'monthly' and (not report_data.month or report_data.month < 1 or report_data.month > 12):
            raise HTTPException(status_code=400, detail="Invalid month for monthly report")
        if report_data.report_type == 'quarterly' and (not report_data.quarter or report_data.quarter < 1 or report_data.quarter > 4):
            raise HTTPException(status_code=400, detail="Invalid quarter for quarterly report")

        # Create or update company info if needed
        if not company_info:
            company_info = CompanyInfo(
                company_name="Company " + tax_number,  # Placeholder name
                tax_number=tax_number,
                post_initiator_user_id=actual_user.id,
                status=True
            )
            db.add(company_info)
            db.commit()
            db.refresh(company_info)

        # Check if report already exists
        existing_report = db.query(CompanyReport).filter(
            CompanyReport.company_tax_number == tax_number,
            CompanyReport.report_type == report_data.report_type,
            CompanyReport.year == report_data.year,
            CompanyReport.month == report_data.month,
            CompanyReport.quarter == report_data.quarter
        ).first()

        if existing_report:
            # Update existing report
            existing_report.report_data = report_data.report_data
            existing_report.updated_at = datetime.now()
            db.commit()
            return {"message": "Report updated successfully", "report_id": existing_report.id}
        else:
            # Create new report
            new_report = CompanyReport(
                user_id=actual_user.id,  # Use actual user ID
                company_tax_number=tax_number,
                report_type=report_data.report_type,
                year=report_data.year,
                month=report_data.month,
                quarter=report_data.quarter,
                report_data=report_data.report_data
            )
            db.add(new_report)
            db.commit()
            db.refresh(new_report)
            return {"message": "Report stored successfully", "report_id": new_report.id}

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store report: {str(e)}")

def create_company_info(app):
    """
    Function to set up the company info request routes
    """
    # Include API routes with /api/v1 prefix
    app.include_router(api_router)
    
    # Include page routes without prefix
    app.include_router(page_router)
    
    return api_router
