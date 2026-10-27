@echo off
chcp 65001 >nul
title ManyPlayer - Instalasi Dependensi Windows
cls

REM Beralih ke direktori utama proyek - root folder
cd /d "%~dp0..\.."

echo ========================================================
echo        ManyPlayer - CCTV Multi-Camera Video Wall
echo            Instalasi Otomatis untuk Windows
echo ========================================================
echo.

REM 1. Periksa ketersediaan Python di sistem
python --version >nul 2>&1
if errorlevel 1 goto :no_python

echo [1/3] Python terdeteksi di sistem:
python --version
echo.

REM 2. Siapkan Virtual Environment .venv
if exist ".venv\Scripts\python.exe" goto :venv_exists

echo [2/3] Membuat virtual environment .venv...
python -m venv .venv
if errorlevel 1 goto :venv_failed
echo     .venv berhasil dibuat.
goto :install_deps

:venv_exists
echo [2/3] Virtual environment .venv sudah tersedia.

:install_deps
echo.
REM 3. Upgrade pip dan instal dependensi
echo [3/3] Menginstal dan memperbarui dependensi...
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto :deps_failed
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto :deps_failed

echo.
echo ========================================================
echo          Instalasi Selesai ^& Siap Digunakan!
echo ========================================================
echo.
echo Cara menjalankan aplikasi:
echo   - Klik 2x "scripts\windows\run.bat"      : Pemantauan kamera live normal
echo   - Klik 2x "scripts\windows\run_mock.bat" : Mode simulasi tanpa kamera fisik
echo   - Klik 2x "scripts\windows\build.bat"    : Kompilasi menjadi ManyPlayer.exe
echo.
pause
exit /b 0

:no_python
echo [ERROR] Python tidak terdeteksi di sistem Windows Anda!
echo.
echo Silakan unduh dan instal Python 3.10 atau versi lebih baru dari:
echo https://www.python.org/downloads/
echo.
echo PENTING: Saat instalasi, pastikan mencentang pilihan:
echo "Add Python to PATH"
echo.
pause
exit /b 1

:venv_failed
echo [ERROR] Gagal membuat virtual environment!
pause
exit /b 1

:deps_failed
echo.
echo [ERROR] Terjadi kesalahan saat mengunduh paket dependensi.
echo Pastikan komputer terhubung ke internet dan coba kembali.
pause
exit /b 1
