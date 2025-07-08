@echo off
echo Installing Relevator dependencies...

echo.
echo 1. Creating virtual environment...
if not exist venv (
    python -m venv venv
    echo Virtual environment created.
) else (
    echo Virtual environment already exists.
)

echo.
echo 2. Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo 3. Installing Python packages...
pip install -r requirements.txt

echo.
echo Dependencies installed successfully!
echo You can now run: .\start.bat
pause 