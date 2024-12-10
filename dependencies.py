from fastapi.templating import Jinja2Templates
import os

# Configure Jinja2 Templates with absolute path
template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
templates = Jinja2Templates(directory=template_path)
