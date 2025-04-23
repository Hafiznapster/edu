#!/bin/bash

echo "Setting up EduConnect application..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Run the setup script
python3 setup.py

echo ""
echo "Installation completed!"
echo "To run the application, activate the virtual environment and run the application:"
echo ""
echo "source venv/bin/activate"
echo "python run.py"
echo ""
echo "Press Enter to exit..."
read
