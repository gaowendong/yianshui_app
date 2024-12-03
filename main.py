from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import sessionmaker
from database import engine, session
import os
from services.auth import check_redis_connection, get_cached_token, redis_client
from services.company_info import query_third_party_system
from typing import Dict, Any
import json
from datetime import datetime

# FastAPI app
app = FastAPI(title="Yi'an Tax System")

# Mount templates directory
templates = Jinja2Templates(directory="templates")

# Create the admin panel
from admin import create_admin
admin = create_admin(app)

# Create the company info request routes
from company_info_request import create_company_info_request
company_info = create_company_info_request(app)

def log_request(message: str, **kwargs):
    """Helper function to log requests with timestamp"""
    timestamp = datetime.now().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "message": message,
        **kwargs
    }
    print(json.dumps(log_entry, indent=2))

@app.middleware("http")
async def check_redis_middleware(request: Request, call_next):
    """
    Middleware to check Redis connection for specific routes
    """
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
    
    response = await call_next(request)
    return response

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """
    Redirect to upload base info page
    """
    return RedirectResponse(url="/upload_base_info")

@app.get("/upload_base_info", response_class=HTMLResponse)
async def upload_base_info_page(request: Request):
    """
    Serve the upload base info page
    """
    return templates.TemplateResponse("upload_base_info.html", {"request": request})

@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    """
    Serve the upload page
    """
    try:
        check_redis_connection()
        return templates.TemplateResponse("upload_company_info.html", {"request": request})
    except HTTPException:
        return RedirectResponse(url="/upload_base_info")

@app.get("/download-report", response_class=HTMLResponse)
async def download_report_page(request: Request):
    """
    Serve the download report page
    """
    try:
        check_redis_connection()
        return templates.TemplateResponse("download_report.html", {"request": request})
    except HTTPException:
        return RedirectResponse(url="/upload_base_info")

@app.post("/api/download-report/{system_user_id}")
async def download_report(system_user_id: int, request: Request):
    """
    Handle report download request
    """
    try:
        log_request("Starting download report request", system_user_id=system_user_id)
        
        # Get request body
        body = await request.json()
        log_request("Request parameters", parameters=body)
        
        # Get token using system_user_id
        token = get_cached_token(system_user_id)
        if token:
            log_request("Token retrieved from cache", 
                       system_user_id=system_user_id,
                       token_preview=f"{token[:10]}...")
        else:
            log_request("Error: Token not found")
            raise HTTPException(status_code=401, detail="Token not found. Please upload base info first.")
        
        # Call the service function
        log_request("Calling query_third_party_system")
        result = await query_third_party_system(
            date_source=body.get("dateSource"),
            date_time=body.get("dateTime"),
            date_type=body.get("dateType"),
            year=body.get("year"),
            token=token
        )
        
        log_request("Query completed successfully", result=result)
        return result
        
    except HTTPException as he:
        log_request("HTTP Exception occurred", error=str(he), status_code=he.status_code)
        raise he
    except Exception as e:
        log_request("Unexpected error occurred", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
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
    """
    Get a list of all routes in the FastAPI app
    """
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
    """
    Handle HTTP exceptions
    """
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
    """
    Handle general exceptions
    """
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
