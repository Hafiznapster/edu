import os
import subprocess
import sys
import venv
from pathlib import Path

def create_virtual_environment():
    """Create a virtual environment for the application."""
    print("Creating virtual environment...")
    venv_dir = Path("venv")
    if venv_dir.exists():
        print("Virtual environment already exists.")
        return
    
    venv.create(venv_dir, with_pip=True)
    print("Virtual environment created successfully.")

def install_dependencies():
    """Install dependencies from requirements.txt."""
    print("Installing dependencies...")
    
    # Determine the Python executable in the virtual environment
    if sys.platform == "win32":
        python_executable = Path("venv") / "Scripts" / "python.exe"
    else:
        python_executable = Path("venv") / "bin" / "python"
    
    # Install dependencies
    subprocess.run([str(python_executable), "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.run([str(python_executable), "-m", "pip", "install", "-r", "requirements.txt"])
    print("Dependencies installed successfully.")

def create_env_file():
    """Create a .env file if it doesn't exist."""
    env_file = Path(".env")
    if env_file.exists():
        print(".env file already exists.")
        return
    
    print("Creating .env file...")
    with open(env_file, "w") as f:
        f.write("SECRET_KEY=your_secret_key_here\n")
        f.write("DATABASE_URL=sqlite:///app.db\n")
        f.write("FLASK_APP=run.py\n")
        f.write("FLASK_ENV=development\n")
    
    print(".env file created successfully.")

def initialize_database():
    """Initialize the database."""
    print("Initializing database...")
    
    # Determine the Python executable in the virtual environment
    if sys.platform == "win32":
        python_executable = Path("venv") / "Scripts" / "python.exe"
        flask_executable = Path("venv") / "Scripts" / "flask.exe"
    else:
        python_executable = Path("venv") / "bin" / "python"
        flask_executable = Path("venv") / "bin" / "flask"
    
    # Initialize database
    subprocess.run([str(flask_executable), "db", "init"])
    subprocess.run([str(flask_executable), "db", "migrate", "-m", "Initial migration"])
    subprocess.run([str(flask_executable), "db", "upgrade"])
    
    print("Database initialized successfully.")

def main():
    """Main function to set up the application."""
    print("Setting up EduConnect application...")
    
    create_virtual_environment()
    install_dependencies()
    create_env_file()
    initialize_database()
    
    print("\nSetup completed successfully!")
    print("You can now run the application with: python run.py")

if __name__ == "__main__":
    main()
