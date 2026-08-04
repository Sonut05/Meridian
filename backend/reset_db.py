import os
import shutil
import glob
import subprocess

def reset_database():
    print("Resetting database...")
    # Delete trip_planner.db
    db_path = "trip_planner.db"
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print("Deleted trip_planner.db")
        except Exception as e:
            print(f"Error deleting db: {e}")

    # Delete alembic version files
    version_files = glob.glob("alembic/versions/*.py")
    for f in version_files:
        try:
            os.remove(f)
            print(f"Deleted version file: {f}")
        except Exception as e:
            print(f"Error deleting {f}: {e}")

    # Run alembic revision --autogenerate -m "Init"
    print("Generating new migration...")
    try:
        res = subprocess.run(
            [".\\venv\\Scripts\\python", "-m", "alembic", "revision", "--autogenerate", "-m", "Init"],
            capture_output=True,
            text=True,
            shell=True
        )
        print("Stdout:", res.stdout)
        print("Stderr:", res.stderr)
    except Exception as e:
        print("Failed to run alembic revision:", e)

    # Run alembic upgrade head
    print("Upgrading database...")
    try:
        res = subprocess.run(
            [".\\venv\\Scripts\\python", "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            shell=True
        )
        print("Stdout:", res.stdout)
        print("Stderr:", res.stderr)
    except Exception as e:
        print("Failed to run alembic upgrade:", e)

if __name__ == "__main__":
    reset_database()
