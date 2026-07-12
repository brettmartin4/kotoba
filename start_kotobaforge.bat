@echo off
REM KotobaForge local launcher.
REM Builds the frontend once, starts the backend (which serves the built
REM frontend as static files), and opens your browser to the app.
REM Closing the "KotobaForge Server" console window stops the app.

setlocal enabledelayedexpansion
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found on PATH. Install Python 3.12+ and try again.
    pause
    exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
    echo Node.js/npm was not found on PATH. Install Node.js LTS and try again.
    pause
    exit /b 1
)

if not exist "backend\.venv\Scripts\python.exe" (
    echo Setting up backend virtual environment, this only happens once...
    python -m venv backend\.venv
    if errorlevel 1 (
        echo Failed to create the backend virtual environment.
        pause
        exit /b 1
    )
    backend\.venv\Scripts\python.exe -m pip install --upgrade pip
    backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
    if errorlevel 1 (
        echo Failed to install backend dependencies.
        pause
        exit /b 1
    )
)

if not exist "frontend\node_modules" (
    echo Installing frontend dependencies, this only happens once...
    pushd frontend
    call npm install
    set NPM_INSTALL_RESULT=!errorlevel!
    popd
    if not "!NPM_INSTALL_RESULT!"=="0" (
        echo Failed to install frontend dependencies.
        pause
        exit /b 1
    )
)

echo Building frontend...
pushd frontend
call npm run build
set NPM_BUILD_RESULT=!errorlevel!
popd
if not "!NPM_BUILD_RESULT!"=="0" (
    echo Frontend build failed.
    pause
    exit /b 1
)

echo Starting KotobaForge server...
start "KotobaForge Server" /D "%~dp0backend" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo Waiting for the server to become ready...
set READY=0
for /l %%i in (1,1,30) do (
    if "!READY!"=="0" (
        curl -s -o nul -w "%%{http_code}" http://127.0.0.1:8000/api/health > "%TEMP%\kotobaforge_health.txt" 2>nul
        set /p HEALTH_CODE=<"%TEMP%\kotobaforge_health.txt"
        if "!HEALTH_CODE!"=="200" (
            set READY=1
        ) else (
            timeout /t 1 /nobreak >nul
        )
    )
)

start http://127.0.0.1:8000

echo KotobaForge should now be open in your browser at http://127.0.0.1:8000
echo The server keeps running in the "KotobaForge Server" window. Close that window to stop KotobaForge.
endlocal
