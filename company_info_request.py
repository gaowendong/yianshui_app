from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from typing import Annotated, List
import asyncio
from datetime import datetime
from pydantic import BaseModel
import json
import traceback

from database import session
from models import QueryResult
from schemas.company import CompanyInfoCreate, CompanyInfoOut
from services.company_info import upload_company_info, query_third_party_system
from services.auth import register_tenant, check_redis_connection, redis_client

# Initialize router
router = APIRouter()

# Dependency to get database session
def get_db():
    db = session()
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

# Login request model
class TenantRegistration(BaseModel):
    companyName: str
    indexStandardType: str
    industry: str
    registrationType: str
    taxpayerNature: str
    taxpayerNo: str

@router.post("/register")
async def register_new_tenant(request: Request, registration_data: TenantRegistration):
    """
    Register a new tenant and get authentication token
    """
    try:
        print("\n=== Starting New Tenant Registration ===")
        print(f"Registration Data: {json.dumps(registration_data.dict(), indent=2)}")
        
        # Check Redis connection first
        print("Checking Redis connection...")
        check_redis_connection()
        print("Redis connection verified")
        
        result = await register_tenant(registration_data.dict())
        print(f"Registration successful: {json.dumps(result, indent=2)}")
        
        # Store user_id in session
        request.session["user_id"] = result["systemUserId"]
        print(f"Stored user_id in session: {result['systemUserId']}")
        
        # Store token in Redis with proper key format
        redis_key = f"yas_token:{result['systemUserId']}"
        token_data = {
            "token": result["token"],
            "systemUserId": result["systemUserId"],
            "tenantId": result["tenantId"],
            "expirationTime": result["expirationTime"]
        }
        redis_client.set(redis_key, json.dumps(token_data))
        print(f"Stored token data in Redis with key: {redis_key}")
        
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

@router.post("/upload-company-info/{user_id}")
async def upload_company_data(
    request: Request,
    user_id: int,
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
        
        # Log request details
        await log_request_details(request, {
            "user_id": user_id,
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
        
        # Check Redis connection first
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

        print("\nAll validations passed, proceeding with upload...")
        
        # Upload each file
        results = []
        for i, file in enumerate(files, 1):
            try:
                print(f"\nProcessing file {i}/{len(files)}: {file.filename}")
                result = await upload_company_info(
                    db=db,
                    user_id=user_id,
                    date_source=date_source,
                    date_type=date_type,
                    year=year,
                    file=file
                )
                results.append({
                    "filename": file.filename,
                    "status": "success",
                    "result": result
                })
                print(f"Successfully uploaded: {file.filename}")
            except Exception as e:
                print(f"Error uploading {file.filename}: {str(e)}")
                print(f"Stack trace: {traceback.format_exc()}")
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "error": str(e)
                })

        # Log final results
        print("\nUpload Results:")
        print(json.dumps(results, indent=2))
        
        # Check if any files failed
        failed_files = [r for r in results if r["status"] == "error"]
        if failed_files:
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "Some files failed to upload",
                    "failed_files": failed_files
                }
            )

        return {
            "status": "success",
            "message": f"Successfully uploaded {len(files)} files",
            "results": results,
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

def create_company_info_request(app):
    """
    Function to set up the company info request routes
    """
    app.include_router(router, prefix="/api/v1", tags=["company_info"])
    return router
