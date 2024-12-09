import httpx
from fastapi import HTTPException, Depends, Request
import redis
from datetime import datetime
import json
import traceback
import socket
from sqlalchemy.orm import Session
from database import SessionLocal
from utils.token_utils import verify_access_token
from models import User

# Initialize Redis connection with error handling
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client.ping()
    print("Successfully connected to Redis")
except redis.ConnectionError as e:
    print(f"Failed to connect to Redis: {e}")
    print("Please ensure Redis server is running")
    redis_client = None
except Exception as e:
    print(f"Unexpected error connecting to Redis: {e}")
    redis_client = None

def get_db():
    """
    Database session dependency
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """
    Get the current authenticated user from the request
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )
    
    token = auth_header.split(" ")[1]
    try:
        payload = verify_access_token(token)
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid token payload"
            )
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        return user
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {str(e)}"
        )

def parse_datetime(datetime_str: str) -> datetime:
    """
    Parse datetime string with microseconds handling
    """
    try:
        # First try parsing with microseconds
        return datetime.strptime(datetime_str.split('+')[0], '%Y-%m-%dT%H:%M:%S.%f')
    except ValueError:
        try:
            # If that fails, try without microseconds
            return datetime.strptime(datetime_str.split('+')[0], '%Y-%m-%dT%H:%M:%S')
        except ValueError as e:
            print(f"Error parsing datetime: {datetime_str}")
            raise e

async def register_tenant(company_data: dict):
    """
    Register tenant with the Yi'an Tax system and store token in Redis
    """
    try:
        print("\n=== Starting Tenant Registration ===")
        print(f"Request Data: {json.dumps(company_data, indent=2)}")
        
        # Ensure Redis is available
        check_redis_connection()
        
        # Make request to external API
        async with httpx.AsyncClient() as client:
            print("\nSending POST request to registration endpoint...")
            response = await client.post(
                'http://test-yas.hthuiyou.com/skServer/yas/tenantid/register',
                json=company_data
            )
            
            print(f"\nResponse Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Response Body: {response.text}")
            
            data = response.json()
            print(f"\nParsed Response Data: {json.dumps(data, indent=2)}")
            
            if data.get('status') == 200:
                print("\nRegistration successful, processing token...")
                token_data = {
                    'token': data['data']['token'],
                    'systemUserId': data['data']['systemUserId'],
                    'userId': company_data.get('userId'),
                    'tenantId': data['data']['tenantId'],
                    'expirationTime': data['data']['expirationTime'],
                    'taxpayerNo': company_data.get('taxpayerNo'),
                    'companyName': company_data.get('companyName'),
                    'indexStandardType': company_data.get('indexStandardType'),
                    'industry': company_data.get('industry'),
                    'registrationType': company_data.get('registrationType'),
                    'taxpayerNature': company_data.get('taxpayerNature')
                }
                
                try:
                    print(f"\nParsing expiration time: {data['data']['expirationTime']}")
                    expiration = parse_datetime(data['data']['expirationTime'])
                    ttl = int((expiration - datetime.utcnow()).total_seconds())
                    
                    print(f"\nStoring token in Redis:")
                    print(f"Key: yas_token:{data['data']['systemUserId']}")
                    print(f"TTL: {ttl} seconds")
                    print(f"Token Data: {json.dumps(token_data, indent=2)}")
                    
                    redis_key = f"yas_token:{data['data']['systemUserId']}"
                    
                    registration_key = f"company_registration:{data['data']['systemUserId']}"
                    registration_data = {
                        'companyName': company_data.get('companyName'),
                        'indexStandardType': company_data.get('indexStandardType'),
                        'industry': company_data.get('industry'),
                        'registrationType': company_data.get('registrationType'),
                        'taxpayerNature': company_data.get('taxpayerNature'),
                        'taxpayerNo': company_data.get('taxpayerNo')
                    }
                    redis_client.setex(
                        registration_key,
                        ttl,
                        json.dumps(registration_data, ensure_ascii=False)
                    )
                    
                    token_json = json.dumps(token_data, ensure_ascii=False)
                    print(f"Formatted token JSON: {token_json}")
                    
                    redis_client.setex(
                        redis_key,
                        ttl,
                        token_json
                    )
                    
                    stored_data = redis_client.get(redis_key)
                    if stored_data:
                        try:
                            parsed_data = json.loads(stored_data)
                            print(f"\nVerified stored token data: {json.dumps(parsed_data, indent=2)}")
                        except json.JSONDecodeError as e:
                            print(f"Error: Stored data is not valid JSON: {stored_data}")
                            raise Exception(f"Failed to store valid JSON token: {e}")
                    else:
                        raise Exception("Failed to verify stored token")
                    
                    return data['data']
                except redis.RedisError as e:
                    print(f"\nRedis error storing token: {str(e)}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Redis error: {str(e)}"
                    )
                except Exception as e:
                    print(f"\nError storing token in Redis: {str(e)}")
                    print(f"Stack trace: {traceback.format_exc()}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to store token in Redis: {str(e)}"
                    )
            else:
                print(f"\nRegistration failed: {data.get('msg', 'Unknown error')}")
                raise HTTPException(status_code=400, detail=data.get('msg', 'Registration failed'))
                
    except HTTPException as he:
        print(f"\nHTTP Exception during registration: {str(he)}")
        raise
    except Exception as e:
        print(f"\nUnexpected error during registration: {str(e)}")
        print(f"Stack trace: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

def check_redis_connection():
    """
    Check if Redis connection is available
    """
    print("\n=== Checking Redis Connection ===")
    if not redis_client:
        raise HTTPException(
            status_code=500,
            detail="Redis connection not available. Please ensure Redis server is running."
        )
    try:
        redis_client.ping()
        print("Redis connection check successful")
        return True
    except redis.RedisError as e:
        print(f"Redis connection error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Lost connection to Redis: {str(e)}"
        )
    except Exception as e:
        print(f"Unexpected error checking Redis: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected Redis error: {str(e)}"
        )

def get_cached_token(system_user_id: int) -> str:
    """
    Get cached token from Redis
    """
    try:
        print(f"\n=== Getting Cached Token ===")
        print(f"Looking for token with system_user_id: {system_user_id}")
        
        check_redis_connection()
        
        redis_key = f"yas_token:{system_user_id}"
        token_data = redis_client.get(redis_key)
        print(f"Retrieved raw token data: {token_data}")
        
        if token_data:
            try:
                data = json.loads(token_data)
                print(f"Parsed token data: {json.dumps(data, indent=2)}")
                return data.get('token')
            except json.JSONDecodeError as e:
                print(f"Error parsing token data: {str(e)}")
                print(f"Invalid token data: {token_data}")
                return None
        
        print("No token found in cache")
        return None
    except redis.RedisError as e:
        print(f"Redis error retrieving token: {str(e)}")
        return None
    except Exception as e:
        print(f"Error retrieving token from Redis: {str(e)}")
        print(f"Stack trace: {traceback.format_exc()}")
        return None

def get_cached_tin(system_user_id: int) -> str:
    """
    Get cached TIN from Redis
    """
    try:
        print(f"\n=== Getting Cached TIN ===")
        print(f"Looking for TIN with system_user_id: {system_user_id}")
        
        check_redis_connection()
        
        redis_key = f"yas_token:{system_user_id}"
        token_data = redis_client.get(redis_key)
        
        if token_data:
            try:
                data = json.loads(token_data)
                tin = data.get('taxpayerNo')
                print(f"Retrieved TIN: {tin}")
                return tin
            except json.JSONDecodeError as e:
                print(f"Error parsing token data: {str(e)}")
                return None
        
        print("No TIN found in cache")
        return None
    except redis.RedisError as e:
        print(f"Redis error retrieving TIN: {str(e)}")
        return None
    except Exception as e:
        print(f"Error retrieving TIN from Redis: {str(e)}")
        print(f"Stack trace: {traceback.format_exc()}")
        return None

def validate_token(token: str) -> bool:
    """
    Validate if token exists in Redis cache
    """
    try:
        print(f"\n=== Validating Token ===")
        print(f"Validating token: {token}")
        
        check_redis_connection()
        
        for key in redis_client.scan_iter("yas_token:*"):
            print(f"Checking key: {key}")
            token_data = redis_client.get(key)
            if token_data:
                try:
                    data = json.loads(token_data)
                    print(f"Found token data: {json.dumps(data, indent=2)}")
                    if data.get('token') == token:
                        print("Token validated successfully")
                        return True
                except json.JSONDecodeError as e:
                    print(f"Error parsing token data for key {key}: {str(e)}")
                    print(f"Invalid token data: {token_data}")
                    continue
        
        print("Token validation failed")
        return False
    except redis.RedisError as e:
        print(f"Redis error during token validation: {str(e)}")
        return False
    except Exception as e:
        print(f"Error during token validation: {str(e)}")
        print(f"Stack trace: {traceback.format_exc()}")
        return False

def decode_token(token: str) -> dict:
    """
    Decode token and return associated data from Redis
    """
    try:
        print(f"\n=== Decoding Token ===")
        print(f"Decoding token: {token}")
        
        check_redis_connection()
        
        for key in redis_client.scan_iter("yas_token:*"):
            print(f"Checking key: {key}")
            token_data = redis_client.get(key)
            if token_data:
                try:
                    data = json.loads(token_data)
                    if data.get('token') == token:
                        print(f"Found token data: {json.dumps(data, indent=2)}")
                        return {
                            'user_id': data['systemUserId'],
                            'tenant_id': data['tenantId'],
                            'expiration_time': data['expirationTime'],
                            'taxpayer_no': data.get('taxpayerNo')
                        }
                except json.JSONDecodeError as e:
                    print(f"Error parsing token data for key {key}: {str(e)}")
                    print(f"Invalid token data: {token_data}")
                    continue
        
        print("Token not found in Redis")
        raise HTTPException(status_code=401, detail="Invalid token")
    except redis.RedisError as e:
        print(f"Redis error during token decoding: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Redis error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error during token decoding: {str(e)}")
        print(f"Stack trace: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error decoding token: {str(e)}")

def clear_user_token(user_id: int) -> bool:
    """
    Clear user's token from Redis
    """
    try:
        print(f"\n=== Clearing User Token ===")
        print(f"Clearing token for user_id: {user_id}")
        
        check_redis_connection()
        
        redis_key = f"yas_token:{user_id}"
        result = redis_client.delete(redis_key)
        
        if result:
            print("Token cleared successfully")
            return True
        
        print("No token found to clear")
        return False
    except redis.RedisError as e:
        print(f"Redis error clearing token: {str(e)}")
        return False
    except Exception as e:
        print(f"Error clearing token: {str(e)}")
        print(f"Stack trace: {traceback.format_exc()}")
        return False
