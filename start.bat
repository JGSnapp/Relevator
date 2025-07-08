@echo off
echo Starting Relevator...

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
echo 3. Installing Python dependencies...
pip install -r requirements.txt

echo.
echo 4. Starting server with Docker Compose...
docker-compose up -d

echo.
echo 5. Waiting for server to start...
timeout /t 5 /nobreak > nul

echo.
echo 6. Starting desktop application...
python desktop_app.py

echo.
echo Relevator stopped.
pause 