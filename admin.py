from sqladmin import ModelView, Admin, BaseView, expose
from sqladmin.authentication import AuthenticationBackend
from models import User, Channel, CompanyInfo, CompanyReport, ReportTransaction
from database import engine
from fastapi import Depends, Request
from services.auth import get_current_user
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from database import SessionLocal
import json
from utils.token_utils import SECRET_KEY, verify_access_token  # Import verify_access_token

def create_admin(app, secret_key: str = SECRET_KEY):
    authentication_backend = AdminAuth(secret_key=secret_key)
    admin = Admin(app, engine, authentication_backend=authentication_backend)

    admin.add_view(UserAdmin)
    admin.add_view(ChannelAdmin)
    admin.add_view(CompanyInfoAdmin)
    admin.add_view(CompanyReportAdmin)
    admin.add_view(ReportTransactionAdmin)
    admin.add_view(DashboardView)

    return admin

class AdminAuth(AuthenticationBackend):
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        super().__init__(secret_key)

    async def authenticate(self, request: Request) -> Optional[str]:
        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                # Check session for admin status
                if request.session.get("is_admin"):
                    return str(request.session.get("user_id"))
                return None

            token = auth_header.split(" ")[1]
            payload = verify_access_token(token)
            user_id = payload.get("user_id")
            
            if not user_id:
                return None

            # Get database session
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user and user.is_admin:
                    return str(user.id)
            finally:
                db.close()
            
            return None
        except Exception as e:
            print(f"Authentication error: {str(e)}")
            return None

    async def login(self, request: Request) -> bool:
        try:
            form = await request.form()
            username = form.get("username")
            password = form.get("password")

            # Get database session
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.username == username).first()
                if user and user.is_admin:
                    request.session["user_id"] = user.id
                    request.session["is_admin"] = True
                    return True
            finally:
                db.close()

            return False
        except Exception as e:
            print(f"Login error: {str(e)}")
            return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

class UserAdmin(ModelView, model=User):
    column_list = [
        User.id,
        User.email,
        User.username,
        User.firstname,
        User.lastname,
        User.is_admin,
        User.role,
        User.channel_id,
        User.first_level_channel_id
    ]
    column_searchable_list = [User.email, User.username]
    column_sortable_list = [User.id, User.email, User.username]
    column_default_sort = 'id'
    form_excluded_columns = ['password']
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-user"

class ChannelAdmin(ModelView, model=Channel):
    column_list = [
        Channel.id,
        Channel.channel_number,
        Channel.channel_name,
        Channel.channel_location,
        Channel.industry,
        Channel.contact_person,
        Channel.contact_number,
        Channel.email,
        Channel.registration_time,
        Channel.balance
    ]
    column_searchable_list = [Channel.channel_number, Channel.channel_name]
    column_sortable_list = [Channel.id, Channel.channel_number, Channel.channel_name]
    column_default_sort = 'id'
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    name = "Channel"
    name_plural = "Channels"
    icon = "fa-solid fa-building"

class CompanyInfoAdmin(ModelView, model=CompanyInfo):
    column_list = [
        CompanyInfo.id,
        CompanyInfo.company_name,
        CompanyInfo.tax_number,
        CompanyInfo.index_standard_type,
        CompanyInfo.industry,
        CompanyInfo.registration_type,
        CompanyInfo.taxpayer_nature,
        CompanyInfo.upload_year,
        CompanyInfo.status,
        CompanyInfo.created_at
    ]
    column_searchable_list = [CompanyInfo.company_name, CompanyInfo.tax_number]
    column_sortable_list = [CompanyInfo.id, CompanyInfo.company_name]
    column_default_sort = 'id'
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    name = "Company Info"
    name_plural = "Company Infos"
    icon = "fa-solid fa-info-circle"

    def on_model_change(self, form, model, is_created):
        # Convert uploaded_files to JSON if it's a string
        if isinstance(model.uploaded_files, str):
            try:
                model.uploaded_files = json.loads(model.uploaded_files)
            except json.JSONDecodeError:
                model.uploaded_files = []

class CompanyReportAdmin(ModelView, model=CompanyReport):
    column_list = [
        CompanyReport.id,
        CompanyReport.processed_by_user_id,
        CompanyReport.company_tax_number,
        CompanyReport.report_type,
        CompanyReport.year,
        CompanyReport.month,
        CompanyReport.quarter,
        CompanyReport.created_at,
        CompanyReport.updated_at
    ]
    can_view_details = True
    can_edit = False
    can_create = False
    can_delete = True
    
    def format_json(self, json_data):
        try:
            if isinstance(json_data, str):
                json_data = json.loads(json_data)
            return json.dumps(json_data, indent=2)
        except:
            return str(json_data)
    
    column_formatters = {
        CompanyReport.report_data: lambda m, a: self.format_json(m.report_data)
    }
    
    column_details_list = [
        CompanyReport.id,
        CompanyReport.processed_by_user_id,
        CompanyReport.company_tax_number,
        CompanyReport.report_type,
        CompanyReport.year,
        CompanyReport.month,
        CompanyReport.quarter,
        CompanyReport.report_data,
        CompanyReport.created_at,
        CompanyReport.updated_at,
        'user',
        'company_info'
    ]
    
class ReportTransactionAdmin(ModelView, model=ReportTransaction):
    column_list = [
        ReportTransaction.id,
        ReportTransaction.user_id,
        ReportTransaction.channel_id,
        ReportTransaction.report_id,
        ReportTransaction.transaction_type,
        ReportTransaction.cost,
        ReportTransaction.created_at
    ]
    column_sortable_list = [ReportTransaction.id, ReportTransaction.created_at]
    column_default_sort = 'id'
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    name = "Report Transaction"
    name_plural = "Report Transactions"
    icon = "fa-solid fa-exchange-alt"

class DashboardView(BaseView):
    name = "Dashboard"
    icon = "fa-solid fa-chart-line"

    @expose("/admin/dashboard")
    def dashboard(self, request: Request):
        db = SessionLocal()
        try:
            total_users = db.query(func.count(User.id)).scalar()
            total_channels = db.query(func.count(Channel.id)).scalar()
            total_reports = db.query(func.count(CompanyReport.id)).scalar()
            total_transactions = db.query(func.count(ReportTransaction.id)).scalar()

            recent_reports = db.query(CompanyReport).order_by(
                CompanyReport.created_at.desc()
            ).limit(5).all()

            recent_transactions = db.query(ReportTransaction).order_by(
                ReportTransaction.created_at.desc()
            ).limit(5).all()

            return self.templates.TemplateResponse(
                "admin/dashboard.html",
                {
                    "request": request,
                    "total_users": total_users,
                    "total_channels": total_channels,
                    "total_reports": total_reports,
                    "total_transactions": total_transactions,
                    "recent_reports": recent_reports,
                    "recent_transactions": recent_transactions
                }
            )
        finally:
            db.close()
