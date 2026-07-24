@echo off
setlocal
cd /d "%~dp0"

echo Building SpotifyLrcOverlay.exe...
python -m PyInstaller --noconfirm --clean spotify_lrc_overlay.spec
if errorlevel 1 (
    echo.
    echo Build failed. If Python or dependencies are missing, run:
    echo python -m pip install -r requirements.txt
    pause
    exit /b 1
)

echo.
echo Done.
echo Final exe:
echo %CD%\dist\SpotifyLrcOverlay.exe
echo.
pause
