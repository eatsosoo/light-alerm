@echo off
setlocal
pushd "%~dp0" || exit /b 1

rem Prefer the project's virtual environment when available.
set "BUILD_PYTHON=python"
if exist "venv\Scripts\python.exe" set "BUILD_PYTHON=venv\Scripts\python.exe"

"%BUILD_PYTHON%" -m PyInstaller --noconfirm app.spec %*
set "BUILD_RESULT=%ERRORLEVEL%"
if not "%BUILD_RESULT%"=="0" (
    echo.
    echo Build failed. Install dependencies using:
    echo "%BUILD_PYTHON%" -m pip install -r requirements.txt
) else (
    if not exist "dist\config.yaml" (
        if exist "config.yaml" (
            copy /y "config.yaml" "dist\config.yaml" >nul
        ) else (
            copy /y "config.yaml.example" "dist\config.yaml" >nul
        )
    )
    echo.
    echo Build complete: "%~dp0dist\LightAlarm.exe"
)

popd
exit /b %BUILD_RESULT%
