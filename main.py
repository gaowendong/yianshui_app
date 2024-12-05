from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, UploadFile, Form, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import SessionLocal, engine
import models
from services.auth import get_cached_token, check_redis_connection, register_tenant, get_cached_tin, redis_client
from utils.auth_utils import get_system_user_id_from_request, verify_password, create_access_token, verify_access_token
from admin import create_admin
from company_info import create_company_info  # Import the router creation function
from starlette.middleware.sessions import SessionMiddleware
import json

# Create FastAPI app instance
app = FastAPI()

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key="your-secret-key-here",  # Replace with a secure secret key
    session_cookie="session",
    max_age=3600  # 1 hour
)

templates = Jinja2Templates(directory="templates")

# Secret key for admin session
SECRET_KEY = "your-secret-key-here"  # Change this to a secure secret key

# Initialize admin interface
admin = create_admin(app, SECRET_KEY)

# Initialize company info routes
company_info_router = create_company_info(app)

# Database Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic models for request validation
class LoginRequest(BaseModel):
    username: str
    password: str

class StoreReportRequest(BaseModel):
    user_id: int
    company_tax_number: str
    report_type: str
    year: int
    month: Optional[int] = None
    quarter: Optional[int] = None
    report_data: dict

class CompanyRegistration(BaseModel):
    companyName: str
    indexStandardType: str
    industry: str
    registrationType: str
    taxpayerNature: str
    taxpayerNo: str

# Routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    """Handle user login"""
    try:
        # Get form data from request body
        form_data = await request.form()
        username = form_data.get('username')
        password = form_data.get('password')

        print(f"Login attempt - Username: {username}")  # Debug log

        if not username or not password:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Username and password are required"}
            )

        # Find user in database
        user = db.query(models.User).filter(models.User.username == username).first()
        
        if user:
            print(f"User found - Stored password hash: {user.password}")  # Debug log
            print(f"Attempting to verify password: {password}")  # Debug log
        else:
            print("User not found in database")  # Debug log

        # Verify user exists and password is correct
        if not user or not verify_password(password, user.password):
            print("Password verification failed")  # Debug log
            return JSONResponse(
                status_code=401,
                content={"status": "error", "message": "Invalid username or password"}
            )
        
        print("Password verified successfully")  # Debug log
        
        # Create access token
        access_token = create_access_token({"user_id": user.id})
        
        # Store user info in session
        request.session["user_id"] = user.id
        request.session["username"] = user.username
        
        # Try to find the system user ID from Redis
        system_user_id = None
        for key in redis_client.scan_iter("yas_token:*"):
            token_data = redis_client.get(key)
            if token_data:
                try:
                    data = json.loads(token_data)
                    # Check both possible field names for system user ID
                    if str(data.get('systemUserId')) == str(user.id) or str(data.get('userId')) == str(user.id):
                        system_user_id = data.get('systemUserId')  # Use systemUserId from token data
                        break
                except json.JSONDecodeError:
                    continue
        
        # Return success response
        response_data = {
            "status": "success",
            "access_token": f"Bearer {access_token}",
            "redirect_url": "/upload_base_info"
        }
        
        # Include system user ID if found
        if system_user_id:
            response_data["systemUserId"] = system_user_id
            print(f"Including system user ID in response: {system_user_id}")
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        print(f"Login error: {str(e)}")  # Debug log
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Login failed: {str(e)}"}
        )

@app.get("/logout")
async def logout(request: Request):
    """Handle user logout"""
    # Clear session data
    request.session.clear()
    
    # Create HTML response with script to clear localStorage
    html_content = """
        <html>
            <script>
                // Clear all authentication data from localStorage
                localStorage.removeItem('access_token');
                localStorage.removeItem('systemUserId');
                // Redirect to login page
                window.location.href = '/login';
            </script>
        </html>
    """
    
    # Create response that clears the cookie and includes the script
    response = HTMLResponse(content=html_content)
    response.delete_cookie("access_token")
    
    return response

@app.get("/upload_base_info", response_class=HTMLResponse)
async def upload_base_info_page(request: Request):
    return templates.TemplateResponse("upload_base_info.html", {"request": request})

@app.get("/upload_company_info", response_class=HTMLResponse)
async def upload_company_info_page(request: Request):
    return templates.TemplateResponse("upload_company_info.html", {"request": request})

@app.get("/download-report", response_class=HTMLResponse)
async def download_report_page(request: Request):
    return templates.TemplateResponse("download_report.html", {"request": request})

@app.get("/api/v1/test-redis")
async def test_redis():
    try:
        check_redis_connection()
        return {"status": "success", "message": "Redis connection successful"}
    except HTTPException as e:
        return {"status": "error", "message": str(e.detail)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/v1/register")
async def register(
    company_data: CompanyRegistration,
    request: Request,
    db: Session = Depends(get_db)
):
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

@app.post("/api/v1/store-report")
async def store_report(
    report_data: StoreReportRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        # Get the system user ID and tax number
        system_user_id = report_data.user_id
        tax_number = report_data.company_tax_number
        
        # First, try to find an existing user by checking CompanyInfo records
        company_info = db.query(models.CompanyInfo).filter(
            models.CompanyInfo.tax_number == tax_number
        ).first()
        
        if company_info and company_info.post_initiator_user_id:
            actual_user = db.query(models.User).filter(
                models.User.id == company_info.post_initiator_user_id
            ).first()
        else:
            # If no existing user found, find any admin user to associate with
            actual_user = db.query(models.User).filter(
                models.User.is_admin == True
            ).first()
            
            if not actual_user:
                # If no admin user exists, create a new system user
                actual_user = models.User(
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
            company_info = models.CompanyInfo(
                company_name="Company " + tax_number,  # Placeholder name
                tax_number=tax_number,
                post_initiator_user_id=actual_user.id,
                status=True
            )
            db.add(company_info)
            db.commit()
            db.refresh(company_info)

        # Check if report already exists
        existing_report = db.query(models.CompanyReport).filter(
            models.CompanyReport.company_tax_number == tax_number,
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
