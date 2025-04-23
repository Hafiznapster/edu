@echo off
echo Setting up EduConnect application...

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH. Please install Python 3.8 or higher.
    exit /b 1
)

REM Run the setup script
python setup.py

echo.
echo Installation completed!
echo To run the application, activate the virtual environment and run the application:
echo.
echo venv\Scripts\activate
echo python run.py
echo.
echo Press any key to exit...
pause >nul
