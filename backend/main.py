"""
Main entry point for ASGI servers (e.g., Uvicorn) when running from the backend directory.
Exposes 'app' from app.main so that both `uvicorn main:app` and `uvicorn app.main:app` work seamlessly.
"""
import sys
from pathlib import Path

# Ensure the backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
