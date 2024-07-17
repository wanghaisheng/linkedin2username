@echo off
SETLOCAL

REM Check if Python is installed
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Python is not installed or not in the system PATH.
    echo Please install Python and make sure it's in your system PATH.
    pause
    exit /b 1
)

REM Check if uvicorn is installed
python -c "import uvicorn" >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Uvicorn is not installed.
    echo Installing uvicorn...
    pip install uvicorn
    IF %ERRORLEVEL% NEQ 0 (
        echo Failed to install uvicorn.
        pause
        exit /b 1
    )
)

REM Start the FastAPI server
echo Starting FastAPI server...
uvicorn server:app --reload

ENDLOCAL
