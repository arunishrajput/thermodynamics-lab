@echo off
setlocal

echo ============================================================
echo  Thermodynamics Lab — Windows Executable Builder
echo ============================================================
echo.

echo [1/3] Installing Python dependencies...
pip install -r requirements.txt pyinstaller
if errorlevel 1 ( echo ERROR: pip install failed. & pause & exit /b 1 )

echo.
echo [2/3] Building executable (this takes ~1-2 minutes)...
pyinstaller --clean ThermodynamicsLab.spec
if errorlevel 1 ( echo ERROR: PyInstaller failed. & pause & exit /b 1 )

echo.
echo [3/3] Done!
echo.
echo  Output:  dist\ThermodynamicsLab.exe
echo.
echo  Plug in your Arduino, then double-click the .exe to launch.
echo  The app auto-detects the COM port — no manual config needed.
echo.
pause
