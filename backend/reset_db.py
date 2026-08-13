import os
import shutil
import glob
import subprocess
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent

def reset_database():
    print("Resetting database...")
    
    # Path to trip_planner.db
    db_path = BACKEND_DIR / "trip_planner.db"
    if db_path.exists():
        try:
            db_path.unlink()
            print(f"Deleted database at {db_path}")
        except Exception as e:
            print(f"Error deleting db: {e}")

    # Delete alembic version files
    version_files = glob.glob(str(BACKEND_DIR / "alembic" / "versions" / "*.py"))
    for f in version_files:
        try:
            os.remove(f)
            print(f"Deleted version file: {f}")
        except Exception as e:
            print(f"Error deleting {f}: {e}")

    # Find venv python path
    python_exe = BACKEND_DIR / "venv" / "Scripts" / "python.exe"
    if not python_exe.exists():
        # Check standard Unix/Mac path
        python_exe = BACKEND_DIR / "venv" / "bin" / "python"
        
    print(f"Using python executable: {python_exe}")

    # Run alembic revision --autogenerate -m "Init"
    print("Generating new migration...")
    try:
        res = subprocess.run(
            [str(python_exe), "-m", "alembic", "revision", "--autogenerate", "-m", "Init"],
            capture_output=True,
            text=True,
            shell=True,
            cwd=str(BACKEND_DIR)
        )
        print("Stdout:", res.stdout)
        print("Stderr:", res.stderr)
    except Exception as e:
        print("Failed to run alembic revision:", e)

    # Run alembic upgrade head
    print("Upgrading database...")
    try:
        res = subprocess.run(
            [str(python_exe), "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            shell=True,
            cwd=str(BACKEND_DIR)
        )
        print("Stdout:", res.stdout)
        print("Stderr:", res.stderr)
    except Exception as e:
        print("Failed to run alembic upgrade:", e)

if __name__ == "__main__":
    reset_database()

