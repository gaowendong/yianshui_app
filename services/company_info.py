import httpx
from fastapi import HTTPException
from config import settings
from models import CompanyInfo, User
from sqlalchemy.orm import Session
from services.auth import get_cached_token, validate_token, redis_client
from datetime import datetime
import json
import traceback

async def upload_company_info(db: Session, user_id: int, date_source: int, date_type: int, year: int, file):
    """
    Upload company information file to external API and store parameters in Redis
    """
    try:
        print("\n=== Starting Company Info Upload ===")
        print(f"User ID: {user_id}")
        print(f"Date Source: {date_source}")
        print(f"Date Type: {date_type}")
        print(f"Year: {year}")
        print(f"File Name: {file.filename}")
        print(f"File Content Type: {file.content_type}")
        
        file_size = len(await file.read())
        await file.seek(0)  # Reset file position after reading
        print(f"File Size: {file_size} bytes")

        # Get and validate token
        print("\nChecking token...")
        token = get_cached_token(user_id)
        if not token:
            error_msg = "Token not found. Please login first."
            print(f"Error: {error_msg}")
            raise HTTPException(status_code=401, detail=error_msg)

        print(f"Found token for user {user_id}")
        print("\nValidating token...")
        
        if not validate_token(token):
            error_msg = "Invalid or expired token. Please login again."
            print(f"Error: {error_msg}")
            raise HTTPException(status_code=401, detail=error_msg)

        print("Token validation successful")

        # Prepare the file upload
        file_content = await file.read()
        await file.seek(0)  # Reset file position after reading
        
        files = {'files': (file.filename, file_content, file.content_type)}
        
        print("\n=== Preparing API Request ===")
        base_url = "http://test-yas.hthuiyou.com/skServer/yas/getexcel/data-impcal"
        params = {
            'dateSource': str(date_source),
            'dateType': str(date_type),
            'year': str(year)
        }
        headers = {'token': token}

        # Construct full URL for logging
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        full_url = f"{base_url}?{query_string}"
        print(f"Full URL: {full_url}")
        print(f"Parameters: {json.dumps(params, indent=2)}")
        print(f"File: {file.filename} ({file.content_type})")
        print(f"Headers: {json.dumps({k: v[:10] + '...' if k == 'token' else v for k, v in headers.items()}, indent=2)}")

        # Make request to the external API with increased timeout
        timeout = httpx.Timeout(120.0, connect=60.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            print("\n=== Sending Request to External API ===")
            try:
                response = await client.post(
                    base_url,
                    params=params,
                    files=files,
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
                    # Try to extract error message from raw response if possible
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
                    "timestamp": datetime.now().isoformat()
                }
                redis_key = f"upload_params:{user_id}"
                redis_client.set(redis_key, json.dumps(upload_params))
                print(f"Stored upload parameters: {json.dumps(upload_params, indent=2)}")
                
                return {
                    "status": response_data.get('status'),
                    "message": response_data.get('msg'),
                    "timestamp": datetime.now().isoformat()
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

async def query_third_party_system(date_source: int, date_time: int, date_type: int, year: int, token: str) -> dict:
    """
    Query the third-party system for risk report
    """
    try:
        print("\n=== Starting Risk Report Download ===")
        print(f"Parameters:")
        print(f"Date Source: {date_source}")
        print(f"Date Time: {date_time}")
        print(f"Date Type: {date_type}")
        print(f"Year: {year}")
        print(f"Token: {token[:10]}...")  # Only show first 10 chars of token

        # Validate token
        print("\nValidating token...")
        if not validate_token(token):
            error_msg = "Invalid or expired token"
            print(f"Error: {error_msg}")
            raise HTTPException(status_code=401, detail=error_msg)

        print("Downloading process, Token validation successful")

        # Prepare API request
        print("\n=== Preparing API Request--download data ===")
        base_url = "http://test-yas.hthuiyou.com/skServer/yas/risk-report/simplified/ow-data"
        
        headers = {
            'token': token,
            'Content-Type': 'application/json'
        }

        data = {
            'dateSource': date_source,
            'dateTime': date_time,
            'dateType': date_type,
            'year': year
        }

        print(f"Request URL: {base_url}")
        print(f"Request Headers: {json.dumps({k: v[:10] + '...' if k == 'token' else v for k, v in headers.items()}, indent=2)}")
        print(f"Request Data: {json.dumps(data, indent=2)}")

        # Make request to the external API
        timeout = httpx.Timeout(30.0, connect=15.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            print("\n=== Sending Request to External API ===")
            try:
                response = await client.post(
                    base_url,
                    json=data,
                    headers=headers,
                    timeout=timeout
                )
                print(f"Response Status Code: {response.status_code}")
                print(f"Response Headers: {dict(response.headers)}")

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
                    raise HTTPException(
                        status_code=500,
                        detail="Invalid JSON response from API"
                    )

                # Check response status
                if response_data.get('status') != 200:
                    error_msg = response_data.get('msg', 'Download failed')
                    print(f"API Error: {error_msg}")
                    raise HTTPException(status_code=400, detail=error_msg)

                # TODO: Store report data in database (to be implemented)
                print("\n=== Report Data Retrieved Successfully ===")
                
                return response_data

            except httpx.TimeoutException:
                error_msg = "Request to external API timed out"
                print(f"Error: {error_msg}")
                raise HTTPException(status_code=504, detail=error_msg)
                
            except httpx.RequestError as e:
                error_msg = f"Error connecting to external API: {str(e)}"
                print(f"Error: {error_msg}")
                raise HTTPException(status_code=502, detail=error_msg)

    except HTTPException as he:
        print(f"\nHTTP Exception during download: {str(he)}")
        raise
    except Exception as e:
        print(f"\nError downloading risk report: {str(e)}")
        print(f"Stack trace: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error downloading risk report: {str(e)}"
        )
