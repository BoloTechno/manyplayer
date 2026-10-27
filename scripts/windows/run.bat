@echo off
chcp 65001 >nul
title ManyPlayer - Pemantauan CCTV Multi-Kamera
cls

REM Beralih ke direktori utama proyek - root folder
cd /d "%~dp0..\.."

REM Periksa apakah .venv sudah terpasang
if exist ".venv\Scripts\python.exe" goto :run_app

echo [PERINGATAN] Virtual environment belum terpasang!
echo Menjalankan instalasi otomatis terlebih dahulu...
echo.
call "%~dp0install.bat"
if not exist ".venv\Scripts\python.exe" goto :env_failed

:run_app
echo Memulai ManyPlayer Video Wall...
.venv\Scripts\python.exe src\main.py %*

if errorlevel 1 goto :app_error
exit /b 0

:app_error
echo.
echo [INFO] Aplikasi ditutup dengan kode keluar: %errorlevel%
pause
exit /b 1

:env_failed
echo [ERROR] Gagal menyiapkan environment. Aplikasi dibatalkan.
pause
exit /b 1
