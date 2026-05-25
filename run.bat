@echo off
chcp 65001 >nul
title VHS CRM v4 - Pest Control System

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║     VHS CRM v4 - Pest Control           ║
echo  ╚══════════════════════════════════════════╝
echo.

:: Tìm Python
py --version >nul 2>&1
if not errorlevel 1 ( set PYTHON=py & goto :found )
python --version >nul 2>&1
if not errorlevel 1 ( set PYTHON=python & goto :found )
python3 --version >nul 2>&1
if not errorlevel 1 ( set PYTHON=python3 & goto :found )

echo [LOI] Khong tim thay Python!
echo Tai tai: https://www.python.org/downloads/
echo Nho tick "Add Python to PATH" khi cai dat.
echo.
pause & exit /b 1

:found
echo [OK] %PYTHON%:
%PYTHON% --version
echo.

:: Luon cap nhat thu vien (bao gom plotly, reportlab, v.v.)
echo [SETUP] Dang kiem tra va cap nhat thu vien...
%PYTHON% -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo.
    echo [LOI] Cai dat that bai. Thu chay lenh nay thu cong:
    echo       pip install -r requirements.txt
    echo.
    pause & exit /b 1
)
echo [OK] Tat ca thu vien da san sang.
echo.

echo  Dang khoi dong VHS CRM...
echo  Trinh duyet se tu dong mo tai: http://localhost:8501
echo  Nhan Ctrl+C de dung.
echo.

%PYTHON% -m streamlit run app.py --server.port 8501 --browser.gatherUsageStats false

echo.
pause
