@echo off
setlocal
cd /d "%~dp0"

rem ASCII messages and CRLF line endings are intentional for Windows cmd.exe.
rem Try the Python launcher first; it does not require Python on PATH.
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if not errorlevel 1 goto :run_launcher

python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if not errorlevel 1 goto :run_python

rem Default Python 3.12 install locations when PATH and launcher are unavailable.
set "SALES_PYTHON=%LocalAppData%\Programs\Python\Python312\python.exe"
if exist "%SALES_PYTHON%" goto :run_local
set "SALES_PYTHON=%ProgramFiles%\Python312\python.exe"
if exist "%SALES_PYTHON%" goto :run_local

echo Python 3.10 or later was not found.
echo For Windows 8.1, install Python 3.12.10.
echo Run the Python installer again and choose Modify to enable the launcher.
echo See README.md for help.
pause
exit /b 1

:run_launcher
echo Starting Sales Management...
echo Open http://localhost:3000 in Chrome or Edge.
echo Keep this window open. Press Ctrl+C to stop.
py -3 server.py %*
goto :finished

:run_python
echo Starting Sales Management...
echo Open http://localhost:3000 in Chrome or Edge.
echo Keep this window open. Press Ctrl+C to stop.
python server.py %*
goto :finished

:run_local
echo Starting Sales Management...
echo Open http://localhost:3000 in Chrome or Edge.
echo Keep this window open. Press Ctrl+C to stop.
"%SALES_PYTHON%" server.py %*
goto :finished

:finished
set "SALES_EXIT=%ERRORLEVEL%"
if "%SALES_EXIT%"=="0" exit /b 0
echo The program could not start. Read the error above.
pause
exit /b %SALES_EXIT%
