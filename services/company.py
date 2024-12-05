from datetime import datetime
import json
import traceback
from typing import List
import httpx
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from redis import Redis

from models import User, CompanyInfo
from services.auth import get_cached_token, validate_token, get_cached_tin

# Initialize Redis client
redis_client = Redis(host='localhost', port=6379, db=0)

async def upload_company_info_batch(db: Session, system_user_id: int, user_id: int, date_source: int, date_type: int, year: int, files: List[UploadFile]):
    """
    Upload company information files in batch to external API and store parameters in Redis
    """
    print("\n in service/company.py upload_company_info_batch")
    try:
        print("\n=== Starting Batch Company Info Upload ===")
        print(f"User ID: {user_id}")
        print(f"Date Source: {date_source}")
        print(f"Date Type: {date_type}")
        print(f"Year: {year}")
        print(f"Files Count: {len(files)}")
        
        # Verify user exists in database
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            error_msg = f"User with ID {user_id} not found in database"
            print(f"Error: {error_msg}")
            raise HTTPException(status_code=404, detail=error_msg)
        print(f"Found user in database: {user.username}")

        # Get and validate token
        print("\nChecking token...")
        token = get_cached_token(system_user_id)
        if not token:
            error_msg = "Token not found. Please login first."
            print(f"Error: {error_msg}")
            raise HTTPException(status_code=401, detail=error_msg)

        # Get TIN from Redis
        tin = get_cached_tin(system_user_id)
        if not tin:
            error_msg = "Taxpayer number not found. Please register first."
            print(f"Error: {error_msg}")
            raise HTTPException(status_code=401, detail=error_msg)

        print(f"Found token and TIN for user {user_id}")
        print("\nValidating token...")
        if not validate_token(token):
            error_msg = "Invalid or expired token. Please login again."
            print(f"Error: {error_msg}")
            raise HTTPException(status_code=401, detail=error_msg)

        print("Token validation successful")

        # Prepare the files for upload
        files_data = []
        for file in files:
            file_content = await file.read()
            files_data.append(('files', (file.filename, file_content, file.content_type)))
            await file.seek(0)  # Reset file position after reading

        # Prepare the API request headers and parameters
        print("\n=== Preparing API Request ===")
        base_url = "http://test-yas.hthuiyou.com/skServer/yas/getexcel/data-impcal"
        params = {
            'dateSource': str(date_source),
            'dateType': str(date_type),
            'year': str(year),
            'taxpayerNo': tin  # Include TIN in API request
        }
        headers = {'token': token}

        # Construct full URL for logging
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        full_url = f"{base_url}?{query_string}"
        print(f"Full URL: {full_url}")
        print(f"Parameters: {json.dumps(params, indent=2)}")
        print(f"Files: {[file.filename for file in files]}")
        print(f"Headers: {json.dumps({k: v[:10] + '...' if k == 'token' else v for k, v in headers.items()}, indent=2)}")

        # Make request to the external API with increased timeout
        timeout = httpx.Timeout(180.0, connect=60.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            print("\n=== Sending Request to External API ===")
            try:
                response = await client.post(
                    base_url,
                    params=params,
                    files=files_data,
                    headers=headers,
                    timeout=timeout
                )
                print(f"Response Status Code: {response.status_code}")
                print(f"Response Headers: {dict(response.headers)}")
                print(f"Request URL: {response.request.url}")

                # Log raw response text first
                raw_response = response.text
                print(f"Raw Response Text: {raw_response}")

                # Check if response is empty
                if not raw_response:
                    print("Empty response received from API")
                    raise HTTPException(
                        status_code=500,
                        detail="Empty response received from API"
                    )

                try:
                    response_data = response.json()
                    print(f"Parsed Response Data: {json.dumps(response_data, indent=2)}")
                except json.JSONDecodeError as e:
                    print(f"JSON Parse Error: {str(e)}")
                    print(f"Failed to parse response: {raw_response}")
                    error_msg = raw_response if raw_response else "Invalid JSON response from API"
                    raise HTTPException(
                        status_code=500,
                        detail=error_msg
                    )

                # Check if the response status is 200 (success)
                if response_data.get('status') != 200:
                    error_msg = response_data.get('msg', 'Upload failed')
                    print(f"API Error: {error_msg}")
                    raise HTTPException(status_code=400, detail=error_msg)

                # Store upload parameters in Redis for later use
                print("\n=== Storing Upload Parameters in Redis ===")
                upload_params = {
                    "dateSource": date_source,
                    "dateType": date_type,
                    "year": year,
                    "taxpayerNo": tin,  # Include TIN in upload parameters
                    "timestamp": datetime.now().isoformat()
                }
                redis_key = f"upload_params:{user_id}"
                redis_client.set(redis_key, json.dumps(upload_params))
                print(f"Stored upload parameters: {json.dumps(upload_params, indent=2)}")

                # Create CompanyInfo records for all files
                print("\n=== Creating CompanyInfo Records ===")
                company_info_records = []
                for file in files:
                    try:
                        company_info = CompanyInfo(
                            company_name=file.filename,
                            tax_number=tin,  # Store TIN in CompanyInfo record
                            post_data=json.dumps(upload_params),
                            post_initiator_user_id=user.id,
                            status=True
                        )
                        db.add(company_info)
                        db.commit()
                        db.refresh(company_info)
                        company_info_records.append(company_info)
                        print(f"Created CompanyInfo record with ID: {company_info.id}")
                    except Exception as e:
                        db.rollback()
                        print(f"Error creating CompanyInfo record for {file.filename}: {str(e)}")
                        raise HTTPException(
                            status_code=500,
                            detail=f"Failed to create CompanyInfo record: {str(e)}"
                        )

                # Return the response data
                return {
                    "status": response_data.get('status'),
                    "message": response_data.get('msg'),
                    "timestamp": datetime.now().isoformat(),
                    "company_info_ids": [company_info.id for company_info in company_info_records]
                }

            except httpx.TimeoutException:
                error_msg = "Request to external API timed out (120s limit)"
                print(f"Error: {error_msg}")
                raise HTTPException(status_code=504, detail=error_msg)

            except httpx.RequestError as e:
                error_msg = f"Error connecting to external API: {str(e)}"
                print(f"Error: {error_msg}")
                raise HTTPException(status_code=502, detail=error_msg)

    except HTTPException as he:
        print(f"\nHTTP Exception occurred: {str(he)}")
        print(f"Stack trace: {traceback.format_exc()}")
        raise
    except Exception as e:
        print(f"\nUnexpected error occurred: {str(e)}")
        print(f"Stack trace: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during company info upload: {str(e)}"
        )

async def query_third_party_system(db: Session, date_source: int, date_time: str, date_type: int, year: int, token: str, current_user: User):
    """
    Query third party system for company information
    """
    print("\n=== Starting Third Party System Query ===")
    try:
        # Validate token and get TIN
        print("\n=== Validating Token ===")
        print(f"Validating token: {token}")

        print("\n=== Checking Redis Connection ===")
        redis_client.ping()
        print("Redis connection check successful")

        # Get token data from Redis by scanning for the token
        token_data = None
        for key in redis_client.scan_iter("yas_token:*"):
            print(f"111 Checking key: {key}")
            token_data_str = redis_client.get(key)
            if token_data_str:
                try:
                    data = json.loads(token_data_str)
                    print(f"Found token data: {json.dumps(data, indent=2)}")
                    print(f"line 224 token in json {data.get('token')}")
                    print(f"line 225 token: {token}")
                    if data.get("token") == token:
                        token_data = data
                        break
                except json.JSONDecodeError:
                    continue

        if not token_data:
            error_msg = "Token data not found in Redis. Please login again."
            print(f"Error: {error_msg}")
            raise HTTPException(status_code=401, detail=error_msg)

        print("in company line 235, Token validated successfully")

        tin = token_data.get('taxpayerNo')
        if not tin:
            error_msg = "Taxpayer number not found in token data. Please register first."
            print(f"Error: {error_msg}")
            raise HTTPException(status_code=401, detail=error_msg)

        # Prepare the API request
        base_url = "http://test-yas.hthuiyou.com/skServer/yas/risk-report/simplified/ow-data"
        
        # Convert parameters to strings and ensure they're not None
        params = {
            'dateSource': str(date_source) if date_source is not None else '0',
            'dateTime': str(date_time) if date_time is not None else '0',
            'dateType': str(date_type) if date_type is not None else '0',
            'year': str(year) if year is not None else str(datetime.now().year),
            'taxpayerNo': tin  # Include TIN in API request
        }
        
        # Add token to headers
        headers = {
            'token': token,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        # Log request details
        print("\n=== Preparing API Request ===")
        print(f"Base URL: {base_url}")
        print(f"Parameters: {json.dumps(params, indent=2)}")
        print(f"Headers: {json.dumps({k: v[:10] + '...' if k == 'token' else v for k, v in headers.items()}, indent=2)}")

        # Make request to the external API with increased timeout
        timeout = httpx.Timeout(60.0, connect=30.0)
        async with httpx.AsyncClient(timeout=timeout, verify=False) as client:
            try:
                response = await client.post(
                    base_url,
                    json=params,
                    headers=headers,
                    timeout=timeout
                )
                print(f"Response Status Code: {response.status_code}")
                print(f"Response Headers: {dict(response.headers)}")

                # Log raw response text
                raw_response = response.text
                print(f"Raw Response Text: {raw_response}")

                # Check if response is empty
                if not raw_response:
                    print("Empty response received from API")
                    raise HTTPException(
                        status_code=500,
                        detail="Empty response received from API"
                    )

                try:
                    response_data = response.json()
                    print(f"Parsed Response Data: {json.dumps(response_data, indent=2)}")
                except json.JSONDecodeError as e:
                    print(f"JSON Parse Error: {str(e)}")
                    print(f"Failed to parse response: {raw_response}")
                    error_msg = raw_response if raw_response else "Invalid JSON response from API"
                    raise HTTPException(
                        status_code=500,
                        detail=error_msg
                    )

                # Check response status
                if response_data.get('status') != 200:
                    error_msg = response_data.get('msg', 'Query failed')
                    print(f"API Error: {error_msg}")
                    raise HTTPException(status_code=400, detail=error_msg)

                return {
                    "status": response_data.get('status'),
                    "msg": response_data.get('msg'),
                    "data": response_data.get('data'),
                    "timestamp": datetime.now().isoformat()
                }

            except httpx.TimeoutException:
                error_msg = "Request to external API timed out"
                print(f"Error: {error_msg}")
                raise HTTPException(status_code=504, detail=error_msg)

            except httpx.RequestError as e:
                error_msg = f"Error connecting to external API: {str(e)}"
                print(f"Error: {error_msg}")
                raise HTTPException(status_code=502, detail=error_msg)

    except HTTPException as he:
        print(f"\nHTTP Exception occurred: {str(he)}")
        print(f"Stack trace: {traceback.format_exc()}")
        raise
    except Exception as e:
        print(f"\nUnexpected error occurred: {str(e)}")
        print(f"Stack trace: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during third party system query: {str(e)}"
        )
