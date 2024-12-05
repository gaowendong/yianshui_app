from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, UploadFile, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import SessionLocal, engine
import models
from services.company import upload_company_info_batch, query_third_party_system
from services.auth import get_cached_token
from utils.auth_utils import get_system_user_id_from_request

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Database Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic models for request validation
class StoreReportRequest(BaseModel):
    user_id: int
    company_tax_number: str
    report_type: str
    year: int
    month: Optional[int] = None
    quarter: Optional[int] = None
    report_data: dict

# Routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/upload_base_info", response_class=HTMLResponse)
async def upload_base_info_page(request: Request):
    return templates.TemplateResponse("upload_base_info.html", {"request": request})

@app.get("/upload_company_info", response_class=HTMLResponse)
async def upload_company_info_page(request: Request):
    return templates.TemplateResponse("upload_company_info.html", {"request": request})

@app.get("/download-report", response_class=HTMLResponse)
async def download_report_page(request: Request):
    return templates.TemplateResponse("download_report.html", {"request": request})

@app.post("/api/v1/upload-company-info/{system_user_id}")
async def upload_company_info(
    system_user_id: int,
    user_id: int = Form(...),
    date_source: int = Form(...),
    date_type: int = Form(...),
    year: int = Form(...),
    files: List[UploadFile] = None,
    db: Session = Depends(get_db)
):
    try:
        result = await upload_company_info_batch(
            db=db,
            system_user_id=system_user_id,
            user_id=user_id,
            date_source=date_source,
            date_type=date_type,
            year=year,
            files=files
        )
        return JSONResponse(content=result)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/download-report/{system_user_id}")
async def download_report(
    system_user_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        # Get request body
        body = await request.json()
        date_source = body.get('dateSource')
        date_time = body.get('dateTime')
        date_type = body.get('dateType')
        year = body.get('year')

        # Get token from cache
        token = get_cached_token(system_user_id)
        if not token:
            raise HTTPException(status_code=401, detail="Token not found. Please login first.")

        # Get current user
        current_user = db.query(models.User).filter(models.User.id == system_user_id).first()
        if not current_user:
            raise HTTPException(status_code=404, detail="User not found")

        # Query third party system
        result = await query_third_party_system(
            db=db,
            date_source=date_source,
            date_time=date_time,
            date_type=date_type,
            year=year,
            token=token,
            current_user=current_user
        )
        return JSONResponse(content=result)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/store-report")
async def store_report(
    report_data: StoreReportRequest,
    db: Session = Depends(get_db)
):
    try:
        # Validate report type
        valid_report_types = ['annual', 'monthly', 'quarterly']
        if report_data.report_type not in valid_report_types:
            raise HTTPException(status_code=400, detail="Invalid report type")

        # Validate month/quarter based on report type
        if report_data.report_type == 'monthly' and (not report_data.month or report_data.month < 1 or report_data.month > 12):
            raise HTTPException(status_code=400, detail="Invalid month for monthly report")
        if report_data.report_type == 'quarterly' and (not report_data.quarter or report_data.quarter < 1 or report_data.quarter > 4):
            raise HTTPException(status_code=400, detail="Invalid quarter for quarterly report")

        # Check if company exists
        company = db.query(models.CompanyInfo).filter(
            models.CompanyInfo.tax_number == report_data.company_tax_number
        ).first()
        if not company:
            # Create new company record if it doesn't exist
            company = models.CompanyInfo(
                company_name="Company " + report_data.company_tax_number,  # Placeholder name
                tax_number=report_data.company_tax_number,
                post_initiator_user_id=report_data.user_id,
                status=True
            )
            db.add(company)
            db.commit()
            db.refresh(company)

        # Check if report already exists
        existing_report = db.query(models.CompanyReport).filter(
            models.CompanyReport.company_tax_number == report_data.company_tax_number,
            models.CompanyReport.report_type == report_data.report_type,
            models.CompanyReport.year == report_data.year,
            models.CompanyReport.month == report_data.month,
            models.CompanyReport.quarter == report_data.quarter
        ).first()

        if existing_report:
            # Update existing report
            existing_report.report_data = report_data.report_data
            existing_report.updated_at = datetime.now()
            db.commit()
            return {"message": "Report updated successfully", "report_id": existing_report.id}
        else:
            # Create new report
            new_report = models.CompanyReport(
                user_id=report_data.user_id,
                company_tax_number=report_data.company_tax_number,
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
