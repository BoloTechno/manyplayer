@echo off
chcp 65001 >nul
title ManyPlayer - Mode Simulasi / Demo
cls

:: Periksa apakah .venv sudah terpasang
if not exist ".venv\Scripts\python.exe" (
    echo [PERINGATAN] Virtual environment belum terpasang!
    echo Menjalankan instalasi otomatis terlebih dahulu...
    echo.
    call install.bat
    if not exist ".venv\Scripts\python.exe" (
        echo [ERROR] Gagal menyiapkan environment. Aplikasi dibatalkan.
        pause
        exit /b 1
    )
)

echo ========================================================
echo           ManyPlayer - Mode Simulasi (--mock)
echo    Menghasilkan feed kamera sintetis untuk pengujian
echo ========================================================
echo.

.venv\Scripts\python.exe src\main.py --mock %*

if %errorlevel% neq 0 (
    echo.
    echo [INFO] Aplikasi ditutup dengan kode keluar: %errorlevel%
    pause
)
