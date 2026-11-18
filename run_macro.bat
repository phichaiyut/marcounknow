@echo off
rem ==========================================================
rem  Robot Hotkey Macro launcher
rem  - asks for Administrator (needed only if your IDE runs as admin)
rem  - finds Python, installs keyboard + pyperclip if missing
rem  - runs macro.py
rem  Usage:  run_macro.bat            normal start (asks for admin)
rem          run_macro.bat noadmin    start without the admin prompt
rem          run_macro.bat check      install + self-test only, do not start
rem ==========================================================
setlocal EnableExtensions
cd /d "%~dp0"
title Robot Macro

rem ---------- 1) Administrator check ----------
if /i "%~1"=="noadmin" goto :find_python
if /i "%~1"=="check" goto :find_python
net session >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Running as Administrator
    goto :find_python
)
if /i "%~1"=="elevated" goto :no_admin
echo [*] Requesting Administrator rights ^(click "Yes" on the UAC prompt^)...
set "MACRO_BAT=%~f0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Start-Process -FilePath $env:MACRO_BAT -ArgumentList 'elevated' -Verb RunAs -ErrorAction Stop; exit 0 } catch { exit 1 }"
if %errorlevel% equ 0 exit /b 0
:no_admin
echo [!] Admin was declined - continuing WITHOUT admin.
echo     Hotkeys still work, but typing into an IDE that runs as Administrator will be blocked.
echo.

:find_python
rem ---------- 2) Find Python ----------
set "PY="
py -3 -c "import sys" >nul 2>&1 && set "PY=py -3"
if defined PY goto :have_python
for %%V in (313 312 311 310 39) do (
    if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" set "PY="%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe""
)
if defined PY goto :have_python
python -c "import sys" >nul 2>&1 && set "PY=python"
if defined PY goto :have_python
echo [X] Python not found. Install Python 3 from https://www.python.org/downloads/
echo     and tick "Add python.exe to PATH" during setup.
pause
exit /b 1

:have_python
echo [OK] Python: %PY%

rem ---------- 3) Check tkinter ----------
%PY% -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo [X] tkinter is missing. Re-run the Python installer and enable "tcl/tk and IDLE".
    pause
    exit /b 1
)

rem ---------- 4) Install libraries if missing ----------
%PY% -c "import keyboard, pyperclip" >nul 2>&1
if not errorlevel 1 (
    echo [OK] keyboard + pyperclip ready
    goto :run
)
echo [*] Installing keyboard + pyperclip ...
%PY% -m pip install --disable-pip-version-check --quiet keyboard pyperclip
if errorlevel 1 (
    echo [!] pip install failed ^(offline?^). macro.py still works:
    echo     clipboard falls back to the Windows API; only TYPE_METHOD='unicode' needs keyboard.
) else (
    echo [OK] Libraries installed
)

:run
rem ---------- 5) Self-test, then run ----------
if /i "%~1"=="check" (
    %PY% "%~dp0macro.py" --selftest
    exit /b
)
%PY% "%~dp0macro.py" --selftest >nul 2>&1
if errorlevel 1 (
    echo [!] Self-test failed - check the MACROS table in macro.py
    %PY% "%~dp0macro.py" --selftest
)
echo.
echo ==========  Robot Macro is running  ==========
echo   Close: Ctrl+Shift+Q   or close the window
echo ===============================================
%PY% "%~dp0macro.py"
if errorlevel 1 (
    echo.
    echo [X] macro.py exited with an error - see the message above.
    pause
)
endlocal
