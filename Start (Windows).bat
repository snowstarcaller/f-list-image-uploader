@echo off
cd /d "%~dp0"
set PY=python
where py >nul 2>nul && set PY=py
if not exist .venv (
  echo First run: setting things up, this takes a minute...
  %PY% -m venv .venv || goto nopython
)
.venv\Scripts\python -m pip install -q --disable-pip-version-check playwright pillow
.venv\Scripts\python flist_uploader.py
if errorlevel 1 pause
exit /b

:nopython
echo.
echo Python isn't installed. Get it from https://www.python.org/downloads/
echo and tick "Add python.exe to PATH" during install, then try again.
pause
