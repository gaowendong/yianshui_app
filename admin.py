from fastapi import FastAPI, Request
from sqladmin import Admin, ModelView
from database import engine, SessionLocal
from models import User, CompanyInfo, QueryResult, RiskReport
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse
from wtforms import SelectField
import logging
import traceback
from fastapi.responses import JSONResponse
from typing import Any, Optional
import json
from utils.auth_utils import verify_password

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app instance
app = FastAPI()

# Admin authentication class
class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> Optional[bool]:
        try:
            form = await request.form()
            username = form.get("username")
            password = form.get("password")
            logger.debug(f"Login attempt for username: {username}")
            
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.username == username).first()
                if user and verify_password(password, user.password):
                    if user.is_admin:
                        # Store both token and admin status in session
                        request.session.update({
                            "token": username,
                            "admin": True,
                            "user_id": user.id
                        })
                        logger.info(f"Successful admin login for user: {username}")
                        return True
                logger.warning(f"Failed login attempt for user: {username}")
                return False
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error in login: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    async def logout(self, request: Request) -> bool:
        try:
            request.session.clear()
            return True
        except Exception as e:
            logger.error(f"Error in logout: {str(e)}")
            return False

    async def authenticate(self, request: Request) -> bool:
        try:
            token = request.session.get("token")
            is_admin = request.session.get("admin", False)
            user_id = request.session.get("user_id")
            
            if not token or not is_admin or not user_id:
                logger.debug("Missing session data")
                return False
                
            # Check if user still exists and is admin
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.username == token).first()
                if user and user.is_admin and user.id == user_id:
                    logger.debug(f"Successfully authenticated admin user: {token}")
                    return True
                logger.debug(f"Failed to authenticate user: {token}")
                return False
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error in authenticate: {str(e)}")
            return False

# User List View in Admin Panel
class UsersAdmin(ModelView, model=User):
    column_list = [User.id, User.username, User.firstname, User.lastname, 
                  User.email, User.role, User.is_admin, User.first_level_channel_id]
    column_searchable_list = [User.username, User.email]
    column_sortable_list = [User.id, User.username, User.email]
    column_default_sort = 'id'
    
    form_columns = [
        User.username, User.password, User.firstname, User.lastname,
        User.email, User.role, User.is_admin, User.first_level_channel_id
    ]
    
    form_overrides = {
        'role': SelectField,
        'first_level_channel_id': SelectField,
    }
    
    form_args = {
        'role': {
            'choices': [
                ('level_1', 'First-Level'),
                ('level_2', 'Second-Level')
            ]
        },
        'first_level_channel_id': {
            'choices': []  # Will be populated in scaffold_form
        }
    }

    async def scaffold_form(self, form_class=None):
        try:
            logger.debug("Starting scaffold_form")
            form = await super().scaffold_form(form_class)
            logger.debug("Base form scaffolded")
            
            db = SessionLocal()
            try:
                first_level_users = db.query(User).filter(User.role == 'level_1').all()
                choices = [(None, '-- Select First Level User --')] + [
                    (str(user.id), f"{user.username} ({user.email})") 
                    for user in first_level_users
                ]
                logger.debug(f"Generated choices: {choices}")
                
                if hasattr(form, 'first_level_channel_id'):
                    form.first_level_channel_id.kwargs['choices'] = choices
                    logger.debug("Set first_level_channel_id choices")
                    
            finally:
                db.close()
            
            logger.debug("Completed scaffold_form")
            return form
            
        except Exception as e:
            logger.error(f"Error in scaffold_form: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    async def on_model_change(self, form: dict, model: Any, is_created: bool, request: Request) -> None:
        try:
            logger.debug(f"Model change - is_created: {is_created}")
            logger.debug(f"Model before change: {model.__dict__}")
            logger.debug(f"Form data: {form}")

            # Handle first_level_channel_id conversion
            if 'first_level_channel_id' in form:
                value = form['first_level_channel_id']
                logger.debug(f"Processing first_level_channel_id value: {value}")
                
                if value == 'None' or value == '' or value is None:
                    logger.debug("Setting first_level_channel_id to None")
                    model.first_level_channel_id = None
                else:
                    try:
                        model.first_level_channel_id = int(value)
                        logger.debug(f"Converted first_level_channel_id to int: {model.first_level_channel_id}")
                    except (ValueError, TypeError) as e:
                        logger.error(f"Error converting first_level_channel_id: {e}")
                        model.first_level_channel_id = None

            # Handle boolean fields
            if 'is_admin' in form:
                model.is_admin = bool(form['is_admin'])
                logger.debug(f"Processed is_admin value: {model.is_admin}")

            # Handle other fields
            for key, value in form.items():
                if key not in ['first_level_channel_id', 'is_admin']:
                    setattr(model, key, value)
                    logger.debug(f"Setting {key} = {value}")

            # Validate role and first_level_channel_id combination
            if model.role == 'level_2' and model.first_level_channel_id is None:
                raise ValueError("Second-Level users must have a First-Level user assigned")

            logger.debug(f"Model after change: {model.__dict__}")

        except Exception as e:
            logger.error(f"Error in on_model_change: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    can_view_details = True
    column_details_list = [
        User.id, User.username, User.firstname, User.lastname,
        User.email, User.role, User.is_admin, User.first_level_channel_id,
        'companies', 'query_results', 'risk_reports'
    ]
    
    can_edit = True
    can_create = True
    can_delete = True

    column_formatters = {
        User.first_level_channel_id: lambda m, a: f"User #{m.first_level_channel_id}" if m.first_level_channel_id else None
    }

class CompanyInfoAdmin(ModelView, model=CompanyInfo):
    column_list = [CompanyInfo.id, CompanyInfo.company_name, CompanyInfo.tax_number,
                  CompanyInfo.status, CompanyInfo.post_initiator_user_id]
    can_view_details = True
    can_edit = True
    can_create = True
    can_delete = True

class QueryResultAdmin(ModelView, model=QueryResult):
    column_list = [QueryResult.id, QueryResult.user_id, QueryResult.company_info_id,
                  QueryResult.created_at]
    can_view_details = True
    can_edit = False
    can_create = False
    can_delete = True

class RiskReportAdmin(ModelView, model=RiskReport):
    column_list = [RiskReport.id, RiskReport.user_id, RiskReport.created_at]
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
        RiskReport.response_data: lambda m, a: self.format_json(m.response_data)
    }
    
    column_details_list = [
        RiskReport.id,
        RiskReport.user_id,
        RiskReport.response_data,
        RiskReport.created_at,
        'user'
    ]

def create_admin(app):
    # Import SECRET_KEY from main app
    from main import SECRET_KEY
    
    authentication_backend = AdminAuth(secret_key=SECRET_KEY)
    admin = Admin(
        app=app,
        engine=engine,
        authentication_backend=authentication_backend,
        base_url="/admin",
        title="Admin Panel",
        debug=True,
        middlewares=[]  # Disable default middlewares to avoid conflicts
    )
    
    admin.add_view(UsersAdmin)
    admin.add_view(CompanyInfoAdmin)
    admin.add_view(QueryResultAdmin)
    admin.add_view(RiskReportAdmin)
    
    return admin
