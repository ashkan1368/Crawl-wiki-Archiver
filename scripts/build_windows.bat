@echo off
REM ============================================================================
REM WikIran Archive — Windows 11 Build & Packaging Script
REM Builds standalone executable via PyInstaller and Windows Installer via Inno Setup
REM ============================================================================

setlocal
echo [1/4] Installing Python dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo [2/4] Running automated QA test suite...
python -m unittest discover -s tests -v
if errorlevel 1 (
    echo [ERROR] Automated tests failed. Aborting build.
    exit /b 1
)

echo [3/4] Generating pre-seeded sample database and Excel template...
python -m wikiran_archive.main --init-db --data-dir ".\sample_data"

echo [4/4] Building standalone Windows 11 executable with PyInstaller...
pyinstaller --noconfirm --clean ^
    --name "WikIranArchive" ^
    --windowed ^
    --add-data "README.md;." ^
    --add-data "OPERATOR_MANUAL_FA.md;." ^
    --add-data "OPERATOR_MANUAL_EN.md;." ^
    wikiran_archive/main.py

echo Build complete: dist\WikIranArchive\WikIranArchive.exe
endlocal
