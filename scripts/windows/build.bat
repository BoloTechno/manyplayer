@echo off
chcp 65001 >nul
title ManyPlayer - Kompilasi Windows Standalone (.exe)
cls

:: Beralih ke direktori utama proyek (root folder)
cd /d "%~dp0..\.."

echo ========================================================
echo        ManyPlayer - CCTV Multi-Camera Video Wall
echo            Kompilasi ke Windows Standalone .exe
echo ========================================================
echo.

:: Periksa apakah .venv sudah terpasang
if not exist ".venv\Scripts\python.exe" (
    echo [PERINGATAN] Virtual environment belum terpasang!
    echo Menjalankan instalasi otomatis terlebih dahulu...
    echo.
    call "%~dp0install.bat"
    if not exist ".venv\Scripts\python.exe" (
        echo [ERROR] Gagal menyiapkan environment. Build dibatalkan.
        pause
        exit /b 1
    )
)

echo [1/2] Memastikan PyInstaller terpasang di .venv...
.venv\Scripts\python.exe -m pip install "pyinstaller>=6.0.0"
if %errorlevel% neq 0 (
    echo [ERROR] Gagal menginstal PyInstaller.
    pause
    exit /b 1
)
echo.

echo [2/2] Memulai kompilasi dengan PyInstaller (build_windows.spec)...
.venv\Scripts\pyinstaller.exe build_windows.spec
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Kompilasi gagal! Periksa pesan error di atas.
    pause
    exit /b 1
)

echo.
echo ========================================================
echo                 Kompilasi Sukses!
echo ========================================================
echo.
echo File aplikasi mandiri Windows siap pakai tersedia di:
echo %CD%\dist\ManyPlayer\ManyPlayer.exe
echo.
echo Catatan:
echo Anda dapat menyalin seluruh isi folder "dist\ManyPlayer"
echo ke komputer Windows lain tanpa perlu menginstal Python.
echo.
pause
