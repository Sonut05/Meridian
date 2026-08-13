import sys
import os

# Add backend directory to sys.path dynamically so FastAPI imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
backend_dir = os.path.join(project_root, "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app
from mangum import Mangum

# Wrap FastAPI ASGI app with Mangum for AWS Lambda/Netlify Serverless
handler = Mangum(app)
