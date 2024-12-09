from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, UploadFile, Form, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import SessionLocal, engine
import models
from services.auth import get_cached_token, check_redis_connection, register_tenant, get_cached_tin, redis_client
from utils.auth_utils import get_system_user_id_from_request, verify_password, create_access_token, verify_access_token
from admin import create_admin
from company_info import create_company_info
import channel
from starlette.middleware.sessions import SessionMiddleware
import json
from utils.token_utils import SECRET_KEY  # Import the shared secret key

# Create FastAPI app instance
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,  # Use the same secret key
    session_cookie="session",
    max_age=3600
)

templates = Jinja2Templates(directory="templates")

# Initialize admin interface with the same secret key
admin = create_admin(app, SECRET_KEY)

# Initialize company info routes
company_info_router = create_company_info(app)

# Mount channel router
app.include_router(channel.router)

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

# Routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/channel/dashboard", response_class=HTMLResponse)
async def channel_dashboard_page(request: Request, db: Session = Depends(get_db)):
    """Render channel dashboard page"""
    return templates.TemplateResponse("channel_dashboard.html", {"request": request})

@app.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    """Handle user login"""
    try:
        form_data = await request.form()
        username = form_data.get('username')
        password = form_data.get('password')

        print(f"Login attempt - Username: {username}")

        if not username or not password:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Username and password are required"}
            )

        user = db.query(models.User).filter(models.User.username == username).first()
        
        if user:
            print(f"User found - ID: {user.id}, Role: {user.role}, Channel: {user.channel_id}")
        else:
            print("User not found in database")

        if not user or not verify_password(password, user.password):
            print("Password verification failed")
            return JSONResponse(
                status_code=401,
                content={"status": "error", "message": "Invalid username or password"}
            )
        
        print("Password verified successfully")
        
        # Create token with user information
        token_data = {
            "user_id": user.id,
            "role": user.role,
            "channel_id": user.channel_id
        }
        access_token = create_access_token(token_data)
        
        # Store user info in session
        request.session["user_id"] = user.id
        request.session["username"] = user.username
        request.session["is_admin"] = user.is_admin
        request.session["role"] = user.role
        request.session["channel_id"] = user.channel_id
        
        system_user_id = None
        for key in redis_client.scan_iter("yas_token:*"):
            token_data = redis_client.get(key)
            if token_data:
                try:
                    data = json.loads(token_data)
                    if str(data.get('systemUserId')) == str(user.id) or str(data.get('userId')) == str(user.id):
                        system_user_id = data.get('systemUserId')
                        break
                except json.JSONDecodeError:
                    continue
        
        # Determine redirect URL based on user role and admin status
        if user.is_admin:
            redirect_url = "/admin"
        elif user.role == "level_1":
            redirect_url = "/channel/dashboard"
        else:
            redirect_url = "/upload_base_info"
        
        response_data = {
            "status": "success",
            "access_token": f"Bearer {access_token}",
            "redirect_url": redirect_url,
            "user": {
                "id": user.id,
                "role": user.role,
                "channel_id": user.channel_id
            }
        }
        
        if system_user_id:
            response_data["systemUserId"] = system_user_id
            print(f"Including system user ID in response: {system_user_id}")
        
        print(f"Login successful - Sending response: {json.dumps(response_data, indent=2)}")
        return JSONResponse(content=response_data)
        
    except Exception as e:
        print(f"Login error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Login failed: {str(e)}"}
        )

@app.get("/logout")
async def logout(request: Request):
    """Handle user logout"""
    request.session.clear()
    
    html_content = """
        <html>
            <script>
                localStorage.removeItem('access_token');
                localStorage.removeItem('systemUserId');
                window.location.href = '/login';
            </script>
        </html>
    """
    
    response = HTMLResponse(content=html_content)
    response.delete_cookie("access_token")
    response.delete_cookie("session")
    
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
