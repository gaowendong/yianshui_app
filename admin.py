from fastapi import FastAPI
from sqladmin import Admin, ModelView
from database import engine
from models import User, CompanyInfo, QueryResult
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from sqlalchemy.orm import sessionmaker
from wtforms import SelectField

# Create FastAPI app instance
app = FastAPI()

# Create a sessionmaker instance
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Admin authentication class
class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
        session = SessionLocal()
        try:
            user = session.query(User).filter(User.username == username).first()
            if user and password == user.password:
                if user.is_admin:
                    request.session.update({"token": user.username})
                    return True
            return False
        finally:
            session.close()

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")
        return token is not None

# User List View in Admin Panel
class UsersAdmin(ModelView, model=User):
    # List view configuration
    column_list = [User.id, User.username, User.firstname, User.lastname, 
                  User.email, User.role, User.is_admin, User.first_level_channel_id]
    column_searchable_list = [User.username, User.email]
    column_sortable_list = [User.id, User.username, User.email]
    column_default_sort = 'id'
    
    # Form configuration
    form_columns = [
        User.username, User.password, User.firstname, User.lastname,
        User.email, User.role, User.is_admin, User.first_level_channel_id
    ]
    
    # Form overrides for specific fields
    form_overrides = {
        'role': SelectField,
        'first_level_channel_id': SelectField,
    }

    # Form widget args
    form_widget_args = {
        'role': {
            'choices': [
                ('level_1', 'First-Level'),
                ('level_2', 'Second-Level')
            ]
        }
    }

    async def scaffold_form(self, form_rules=None):
        form = await super().scaffold_form(form_rules)
        
        # Get first-level users for the dropdown
        session = SessionLocal()
        try:
            first_level_users = session.query(User).filter(User.role == 'level_1').all()
            choices = [(None, '-- Select First Level User --')] + [
                (str(user.id), f"{user.username} ({user.email})") 
                for user in first_level_users
            ]
            
            if hasattr(form, 'first_level_channel_id'):
                form.first_level_channel_id.kwargs['choices'] = choices
                
        finally:
            session.close()
        
        return form

    # Details view configuration
    can_view_details = True
    column_details_list = [
        User.id, User.username, User.firstname, User.lastname,
        User.email, User.role, User.is_admin, User.first_level_channel_id,
        'companies', 'query_results'
    ]
    
    # Edit view configuration
    can_edit = True
    
    # Create view configuration
    can_create = True
    
    # Delete configuration
    can_delete = True

    # Custom formatters for display
    column_formatters = {
        User.first_level_channel_id: lambda m, a: f"User #{m.first_level_channel_id}" if m.first_level_channel_id else None
    }

# Company Info Admin View
class CompanyInfoAdmin(ModelView, model=CompanyInfo):
    column_list = [CompanyInfo.id, CompanyInfo.company_name, CompanyInfo.tax_number,
                  CompanyInfo.status, CompanyInfo.post_initiator_user_id]
    can_view_details = True
    can_edit = True
    can_create = True
    can_delete = True

# Query Results Admin View
class QueryResultAdmin(ModelView, model=QueryResult):
    column_list = [QueryResult.id, QueryResult.user_id, QueryResult.company_info_id,
                  QueryResult.created_at]
    can_view_details = True
    can_edit = False
    can_create = False
    can_delete = True

# Function to set up the admin panel
def create_admin(app):
    # Create authentication backend for admin panel
    authentication_backend = AdminAuth(secret_key="supersecretkey")
    admin = Admin(
        app=app,
        engine=engine,
        authentication_backend=authentication_backend,
        base_url="/admin",
        title="Admin Panel"
    )
    
    # Add model views to admin
    admin.add_view(UsersAdmin)
    admin.add_view(CompanyInfoAdmin)
    admin.add_view(QueryResultAdmin)
    
    return admin
