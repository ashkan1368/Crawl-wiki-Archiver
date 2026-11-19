@echo off
chcp 65001 >nul
title WikIran Archive - Windows Installer Build Script (PyInstaller + Inno Setup)
echo ============================================================================
echo   WIKIRAN ARCHIVE - AUTOMATED WINDOWS INSTALLER (.EXE) BUILD SCRIPT
echo ============================================================================
echo.

cd /d "%~dp0\.."

echo [Step 1/4] Checking Python environment and dependencies...
if not exist ".venv" (
    python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller

echo [Step 2/4] Initializing and seeding pre-packaged SQLite database...
python -m wikiran_archive.main --init-db

echo [Step 3/4] Building standalone WikIranArchive.exe via PyInstaller...
pyinstaller --noconfirm --clean --windowed --name "WikIranArchive" ^
    --add-data "OPERATOR_MANUAL_EN.md;." ^
    --add-data "OPERATOR_MANUAL_FA.md;." ^
    wikiran_archive/main.py

echo [Step 4/4] Compiling single-file Windows Installer (WikIranArchive_Setup.exe) via Inno Setup...
set "ISCC_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "%ISCC_PATH%" (
    "%ISCC_PATH%" "installer\wikiran_archive_setup.iss"
    echo.
    echo [SUCCESS] Installer compiled at: installer\installer_output\WikIranArchive_Setup.exe
) else (
    echo [INFO] Inno Setup ISCC.exe not found at default path; generating self-contained PE32+ WikIranArchive_Setup.exe via Python packager...
    python -m wikiran_archive.main --api windows_installer_exe
)

echo.
echo ============================================================================
echo   BUILD COMPLETE!
echo ============================================================================
pause
