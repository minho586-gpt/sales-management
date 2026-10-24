@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if not errorlevel 1 (
    echo 영업관리 시스템을 시작합니다.
    echo 브라우저 주소창에 http://localhost:3000 을 입력하세요.
    echo 종료하려면 Ctrl+C를 누르세요.
    py -3 server.py %*
    goto finished
)

python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if not errorlevel 1 (
    echo 영업관리 시스템을 시작합니다.
    echo 브라우저 주소창에 http://localhost:3000 을 입력하세요.
    echo 종료하려면 Ctrl+C를 누르세요.
    python server.py %*
    goto finished
)

echo Python 3.10 이상을 찾지 못했습니다.
echo https://www.python.org/downloads/ 에서 Python을 설치하세요.
echo 설치할 때 Add python.exe to PATH 항목을 선택하세요.
pause
exit /b 1

:finished
if errorlevel 1 (
    echo 실행 중 오류가 발생했습니다. 위의 오류 내용을 확인하세요.
    pause
)
endlocal
