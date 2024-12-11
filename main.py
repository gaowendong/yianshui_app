from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, UploadFile, Form, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import SessionLocal, engine
import models
from services.auth import get_cached_token, check_redis_connection, register_tenant, get_cached_tin, redis_client
from services.top_level_admin import TopLevelAdminService
from utils.auth_utils import get_system_user_id_from_request, verify_password, create_access_token, verify_access_token
from admin import create_admin
from company_info import create_company_info
import channel
from starlette.middleware.sessions import SessionMiddleware
import json
from utils.token_utils import SECRET_KEY
import os
from routes.top_level_admin import router as top_level_admin_router
from routes.second_level_user import router as second_level_user_router
from dependencies import templates, get_db

# Import internationalization utilities
from i18n import translation_manager, gettext as _

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
    secret_key=SECRET_KEY,
    session_cookie="session",
    max_age=3600
)

# Configure static files
static_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Get Chinese translations
translations = translation_manager.get_translations('zh')

# Add translation function to Jinja2 environment
templates.env.globals['_'] = translations.gettext
templates.env.globals['gettext'] = translations.gettext
templates.env.globals['ngettext'] = translations.ngettext

# Middleware to detect and set locale
@app.middleware("http")
async def add_locale_to_request(request: Request, call_next):
    request.state.locale = 'zh'
    request.state.gettext = translations.gettext
    response = await call_next(request)
    return response

# Initialize admin interface with the same secret key
admin = create_admin(app, SECRET_KEY)

# Initialize company info routes
company_info_router = create_company_info(app)

# Mount routers
app.include_router(channel.router)
app.include_router(top_level_admin_router)
app.include_router(second_level_user_router)

# Routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("login.html", {
        "request": request,
        "locale": 'zh',
        "_": translations.gettext
    })

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {
        "request": request,
        "locale": 'zh',
        "_": translations.gettext
    })

@app.get("/channel/dashboard", response_class=HTMLResponse)
async def channel_dashboard_page(request: Request, db: Session = Depends(get_db)):
    """Render channel dashboard page"""
    return templates.TemplateResponse("channel_dashboard.html", {
        "request": request,
        "locale": 'zh',
        "_": translations.gettext
    })

@app.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    """Handle user login"""
    try:
        form_data = await request.form()
        username = form_data.get('username').strip()  # Add strip() to remove whitespace
        password = form_data.get('password')

        print(f"Login attempt - Username: {username}")

        if not username or not password:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error", 
                    "message": translations.gettext("Username and password are required")
                }
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
                content={
                    "status": "error", 
                    "message": translations.gettext("Invalid username or password")
                }
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
        
        # Determine redirect URL based on user role and admin status
        if user.is_top_level_admin:
            redirect_url = "/topadmin/dashboard"
        elif user.is_admin:
            redirect_url = "/admin"
        elif user.role == "level_1":
            redirect_url = "/channel/dashboard"
        elif user.role == "level_2":
            redirect_url = "/second-level/dashboard"
        else:
            redirect_url = "/upload_base_info"
        
        response_data = {
            "status": "success",
            "access_token": f"Bearer {access_token}",
            "redirect_url": redirect_url,
            "user": {
                "id": user.id,
                "role": user.role,
                "channel_id": user.channel_id,
                "is_top_level_admin": user.is_top_level_admin
            }
        }
        
        print(f"Login successful - Sending response: {json.dumps(response_data, indent=2)}")
        return JSONResponse(content=response_data)
        
    except Exception as e:
        print(f"Login error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error", 
                "message": translations.gettext("Login failed")
            }
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
