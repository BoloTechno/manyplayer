@echo off
chcp 65001 >nul
title ManyPlayer - Pemantauan CCTV Multi-Kamera
cls

:: Beralih ke direktori utama proyek (root folder)
cd /d "%~dp0..\.."

:: Periksa apakah .venv sudah terpasang
if not exist ".venv\Scripts\python.exe" (
    echo [PERINGATAN] Virtual environment belum terpasang!
    echo Menjalankan instalasi otomatis terlebih dahulu...
    echo.
    call "%~dp0install.bat"
    if not exist ".venv\Scripts\python.exe" (
        echo [ERROR] Gagal menyiapkan environment. Aplikasi dibatalkan.
        pause
        exit /b 1
    )
)

echo Memulai ManyPlayer Video Wall...
.venv\Scripts\python.exe src\main.py %*

if %errorlevel% neq 0 (
    echo.
    echo [INFO] Aplikasi ditutup dengan kode keluar: %errorlevel%
    pause
)
