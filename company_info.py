from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from typing import Annotated, List
from datetime import datetime
from pydantic import BaseModel
import json
import traceback

from database import SessionLocal
from models import User
from services.company import upload_company_info_batch, query_third_party_system
from services.auth import register_tenant, check_redis_connection, redis_client, decode_token, get_cached_token, get_cached_tin
from utils.auth_utils import verify_user_ids

# Initialize router
router = APIRouter()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def log_request_details(request: Request, body_data: dict = None):
    """
    Log comprehensive request details
    """
    print("\n=== Detailed Request Log ===")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Method: {request.method}")
    print(f"URL: {request.url}")
    print(f"Client Host: {request.client.host}")
    
    print("\nHeaders:")
    for name, value in request.headers.items():
        print(f"  {name}: {value}")
    
    print("\nQuery Params:")
    for name, value in request.query_params.items():
        print(f"  {name}: {value}")
    
    if body_data:
        print("\nBody Data:")
        print(json.dumps(body_data, indent=2))
    
    print("===========================")

@router.get("/test-redis")
async def test_redis():
    """
    Test Redis functionality
    """
    try:
        print("\n=== Testing Redis Functionality ===")
        
        # Check Redis connection
        check_redis_connection()
        print("Redis connection check passed")
        
        # Try to set and get a test value
        test_key = "test_key"
        test_value = f"test_value_{datetime.now().isoformat()}"
        print(f"Setting test value: {test_key} = {test_value}")
        
        redis_client.set(test_key, test_value)
        print("Successfully set test value")
        
        retrieved_value = redis_client.get(test_key)
        print(f"Retrieved test value: {retrieved_value}")
        
        if retrieved_value == test_value:
            print("Test successful - values match")
            return {
                "status": "success",
                "message": "Redis is working correctly",
                "test_value_set": test_value,
                "test_value_retrieved": retrieved_value,
                "timestamp": datetime.now().isoformat()
            }
        else:
            print(f"Test failed - values don't match. Expected {test_value}, got {retrieved_value}")
            raise HTTPException(
                status_code=500,
                detail="Redis test failed - stored and retrieved values don't match"
            )
            
    except Exception as e:
        print(f"Error testing Redis: {str(e)}")
        print(f"Stack trace: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Redis test failed: {str(e)}"
        )

@router.get("/get-tin/{system_user_id}")
async def get_tin(system_user_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Get the taxpayer identification number (TIN) for a system user
    """
    try:
        print(f"\n=== Getting TIN for System User ID: {system_user_id} ===")
        
        # Verify user IDs and get database user
        real_user_id, database_user = await verify_user_ids(system_user_id, request, db)
        print(f"Database User ID: {real_user_id}")
        print(f"Database Username: {database_user.username}")
        
        # Get TIN from Redis
        tin = get_cached_tin(system_user_id)
        if not tin:
            error_msg = "Taxpayer number not found. Please register first."
            print(f"Error: {error_msg}")
            raise HTTPException(status_code=404, detail=error_msg)
            
        print(f"Found TIN: {tin}")
        return {
            "status": "success",
            "tin": tin,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException as he:
        print(f"\nHTTP Exception getting TIN: {str(he)}")
        raise
    except Exception as e:
        print(f"\nUnexpected error getting TIN: {str(e)}")
        print(f"Stack trace: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get TIN: {str(e)}"
        )

# Login request model
class TenantRegistration(BaseModel):
    companyName: str
    indexStandardType: str
    industry: str
    registrationType: str
    taxpayerNature: str
    taxpayerNo: str

# Report request model
class ReportRequest(BaseModel):
    dateSource: int
    dateTime: str
    dateType: int
    year: int

@router.post("/register")
async def register_new_tenant(request: Request, registration_data: TenantRegistration):
    """
    Register a new tenant and get authentication token
    """
    print("\n=== company_info.py - in register_new_tenant method. ===")
    try:
        print("\n=== Starting New Tenant Registration ===")
        print(f"Registration Data: {json.dumps(registration_data.dict(), indent=2)}")
        
        # Check Redis connection first
        print("Checking Redis connection...")
        check_redis_connection()
        print("Redis connection verified")
        
        # Register tenant - this will handle Redis storage
        result = await register_tenant(registration_data.dict())
        print(f"Registration successful: {json.dumps(result, indent=2)}")
        
        return {
            "status": 200,
            "msg": "Registration successful",
            "data": result
        }
    except HTTPException as he:
        print(f"HTTP Exception during registration: {str(he.detail)}")
        raise
    except Exception as e:
        print(f"Unexpected error during registration: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/upload-company-info/{system_user_id}")
async def upload_company_data(
    system_user_id: int,
    request: Request,
    date_source: Annotated[int, Form()],
    date_type: Annotated[int, Form()],
    year: Annotated[int, Form()],
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload company information files with required parameters
    """
    try:
        print("\n=== Starting Company Info Upload ===")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"System User ID (Yi'an session): {system_user_id}")
        
        # Verify both user IDs and get database user
        real_user_id, database_user = await verify_user_ids(system_user_id, request, db)
        print(f"Database User ID: {real_user_id}")
        print(f"Database Username: {database_user.username}")
        
        # Log request details
        await log_request_details(request, {
            "system_user_id": system_user_id,
            "database_user_id": real_user_id,
            "date_source": date_source,
            "date_type": date_type,
            "year": year,
            "files": [
                {
                    "filename": file.filename,
                    "content_type": file.content_type,
                    "size": len(await file.read())
                }
                for file in files
            ]
        })
        
        # Reset file positions after reading
        for file in files:
            await file.seek(0)
        
        # Check Redis connection
        print("\nChecking Redis connection...")
        check_redis_connection()
        print("Redis connection verified")

        # Validate parameters
        print("\nValidating parameters...")
        if date_source not in [0, 1]:
            error_msg = f"Invalid date_source: {date_source}"
            print(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
            
        if date_type not in [0, 1, 2]:
            error_msg = f"Invalid date_type: {date_type}"
            print(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
            
        if not 2000 <= year <= 2100:
            error_msg = f"Invalid year: {year}"
            print(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Validate number of files
        print("\nValidating files...")
        required_files = 6 if date_type in [0, 1] else 4  # 6 files for Year/Quarter, 4 for Month
        if len(files) != required_files:
            error_msg = f"Invalid number of files: {len(files)}, expected {required_files}"
            print(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Validate file types
        for file in files:
            print(f"Checking file: {file.filename}")
            if not file.filename.endswith(('.xls', '.xlsx')):
                error_msg = f"Invalid file type for {file.filename}. Only .xls and .xlsx files are allowed"
                print(error_msg)
                raise HTTPException(status_code=400, detail=error_msg)

        print("\nAll validations passed, proceeding with batch upload...")
        
        # Use the new batch upload function
        result = await upload_company_info_batch(
            db=db,
            system_user_id=system_user_id,
            user_id=real_user_id,
            date_source=date_source,
            date_type=date_type,
            year=year,
            files=files
        )

        return {
            "status": "success",
            "message": f"Successfully uploaded {len(files)} files",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException as he:
        print(f"\nHTTP Exception during upload: {str(he.detail)}")
        raise
    except Exception as e:
        print(f"\nUnexpected error during upload: {str(e)}")
        print(f"Stack trace: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.post("/download-report/{system_user_id}")
async def download_report(
    system_user_id: int,
    request: Request,
    report_data: ReportRequest,
    db: Session = Depends(get_db)
):
    """Handle report download request"""
    try:
        print("\n=== Starting Report Download ===")
        print(f"System User ID: {system_user_id}")
        print(f"Report Data: {json.dumps(report_data.dict(), indent=2)}")
        
        # Verify both user IDs and get database user
        real_user_id, database_user = await verify_user_ids(system_user_id, request, db)
        print(f"Database User ID: {real_user_id}")
        print(f"Database Username: {database_user.username}")
        
        # Log full request details
        await log_request_details(request, report_data.dict())
        
        # Check Redis connection
        print("\nChecking Redis connection...")
        check_redis_connection()
        print("Redis connection verified")
        
        # Get and validate token
        print("\nGetting token from cache...")
        token = get_cached_token(system_user_id)
        if not token:
            error_msg = "Token not found. Please upload base info first."
            print(f"Error: {error_msg}")
            raise HTTPException(status_code=401, detail=error_msg)
        print("Token retrieved successfully")
        
        # Validate parameters
        print("\nValidating parameters...")
        if report_data.dateSource not in [0, 1]:
            error_msg = f"Invalid dateSource: {report_data.dateSource}"
            print(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
            
        if report_data.dateType not in [0, 1]:
            error_msg = f"Invalid dateType: {report_data.dateType}"
            print(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
            
        if not 2000 <= report_data.year <= 2100:
            error_msg = f"Invalid year: {report_data.year}"
            print(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        
        print("\nAll validations passed, calling query_third_party_system")
        result = await query_third_party_system(
            db=db,
            date_source=report_data.dateSource,
            date_time=report_data.dateTime,
            date_type=report_data.dateType,
            year=report_data.year,
            token=token,
            current_user=database_user
        )
        
        print("Query completed successfully")
        print(f"Result: {json.dumps(result, indent=2)}")
        return result
        
    except HTTPException as he:
        print(f"\nHTTP Exception occurred: {str(he)}")
        print(f"Stack trace: {traceback.format_exc()}")
        raise he
    except Exception as e:
        print(f"\nUnexpected error occurred: {str(e)}")
        print(f"Stack trace: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

def create_company_info(app):
    """
    Function to set up the company info request routes
    """
    app.include_router(router, prefix="/api/v1", tags=["company_info"])
    return router
