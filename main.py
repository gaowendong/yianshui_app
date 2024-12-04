from fastapi import FastAPI, Request, HTTPException, Depends, status
# from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database import get_db
import os
from services.auth import check_redis_connection, clear_user_token
# from services.company import query_third_party_system
# import json
# from datetime import datetime
from models import User
from utils.auth_utils import verify_password, create_access_token, get_current_user
import logging
import traceback
from starlette.middleware.sessions import SessionMiddleware

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Secret key for both session middleware and admin auth
SECRET_KEY = "supersecretkey"

# FastAPI app
app = FastAPI(title="易安税系统")

# Add SessionMiddleware
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    max_age=3600  # Session expiry time in seconds
)

# Mount templates directory
templates = Jinja2Templates(directory="templates")

# Create the admin panel
from admin import create_admin
admin = create_admin(app)

# Create the company info request routes
from company_info import create_company_info
company_info = create_company_info(app)

@app.middleware("http")
async def middleware_handler(request: Request, call_next):
    """Combined middleware for logging and Redis checks"""
    try:
        # Log request
        logger.info(f"Request: {request.method} {request.url}")
        if request.method in ["POST", "PUT"]:
            try:
                body = await request.body()
                if body:
                    logger.debug(f"Request body: {body.decode()}")
            except Exception as e:
                logger.debug(f"Could not log request body: {str(e)}")

        # Check for auth token in cookies and set header
        auth_cookie = request.cookies.get("Authorization")
        if auth_cookie and not request.headers.get("Authorization"):
            request.headers.__dict__["_list"].append(
                (b"authorization", auth_cookie.encode())
            )

        # Check Redis for protected paths
        protected_paths = ["/upload", "/api/v1/register", "/api/v1/upload-company-info", "/download-report"]
        if request.url.path in protected_paths:
            try:
                check_redis_connection()
            except HTTPException as he:
                if request.url.path.startswith("/api/"):
                    return JSONResponse(
                        status_code=he.status_code,
                        content={"detail": str(he.detail)}
                    )
                return RedirectResponse(url="/upload_base_info")
        
        # Process request
        response = await call_next(request)
        
        # Log response
        logger.info(f"Response status: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Error in middleware: {str(e)}")
        logger.error(traceback.format_exc())
        raise


@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access_token = create_access_token(data={"user_id": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/logout")
async def logout(request: Request, current_user: User = Depends(get_current_user)):
    """Handle user logout"""
    try:
        # Clear Redis token
        clear_user_token(current_user.id)
        
        # Clear session
        request.session.clear()
        
        # Create response that redirects to login
        response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
        # Clear auth cookie
        response.delete_cookie(key="Authorization")
        
        return response
    except Exception as e:
        logger.error(f"Error during logout: {str(e)}")
        raise HTTPException(status_code=500, detail="Error during logout")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Redirect to upload base info page"""
    return RedirectResponse(url="/upload_base_info")

@app.get("/upload_base_info", response_class=HTMLResponse)
async def upload_base_info_page(request: Request, current_user: User = Depends(get_current_user)):
    """Serve the upload base info page"""
    try:
        return templates.TemplateResponse("upload_base_info.html", {"request": request, "user": current_user})
    except HTTPException:
        return RedirectResponse(url="/login")

@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request, current_user: User = Depends(get_current_user)):
    """Serve the upload page"""
    try:
        check_redis_connection()
        return templates.TemplateResponse("upload_company_info.html", {"request": request, "user": current_user})
    except HTTPException:
        return RedirectResponse(url="/login")

@app.get("/download-report", response_class=HTMLResponse)
async def download_report_page(request: Request, current_user: User = Depends(get_current_user)):
    """Serve the download report page"""
    try:
        check_redis_connection()
        return templates.TemplateResponse("download_report.html", {"request": request, "user": current_user})
    except HTTPException:
        return RedirectResponse(url="/login")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Serve the login page"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login", response_class=HTMLResponse)
async def login_user(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Process login form"""
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid username or password"})
    
    access_token = create_access_token(data={"user_id": user.id})
    
    # Set up session data for admin users
    if user.is_admin:
        request.session.update({
            "token": user.username,
            "admin": True,
            "user_id": user.id
        })
        logger.debug(f"Set admin session data for user: {user.username}")
        redirect_url = "/admin"
    else:
        redirect_url = "/upload_base_info"
    
    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="Authorization", value=f"Bearer {access_token}", httponly=True)
    
    return response

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        check_redis_connection()
        redis_status = "healthy"
    except:
        redis_status = "unhealthy"

    return {
        "status": "healthy",
        "service": "Yi'an Tax System",
        "components": {
            "redis": redis_status
        }
    }

@app.get("/routes")
async def get_routes():
    """Get a list of all routes in the FastAPI app"""
    routes = []
    for route in app.routes:
        routes.append({
            "path": route.path,
            "methods": route.methods if hasattr(route, "methods") else None
        })
    return {"routes": routes}

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": str(exc.detail)}
        )
    
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "status_code": exc.status_code,
            "detail": exc.detail
        },
        status_code=exc.status_code
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"General Exception: {str(exc)}")
    logger.error(traceback.format_exc())
    
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc)}
        )
    
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "status_code": 500,
            "detail": str(exc)
        },
        status_code=500
    )
