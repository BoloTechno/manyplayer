@echo off
chcp 65001 >nul
title ManyPlayer - Instalasi Dependensi Windows
cls

echo ========================================================
echo        ManyPlayer - CCTV Multi-Camera Video Wall
echo            Instalasi Otomatis untuk Windows
echo ========================================================
echo.

:: 1. Periksa ketersediaan Python di sistem
python --version >nul 2>&1
if %errorlevel% neq 0 (
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
)

echo [1/3] Python terdeteksi di sistem:
python --version
echo.

:: 2. Siapkan Virtual Environment (.venv)
if not exist ".venv\Scripts\python.exe" (
    echo [2/3] Membuat virtual environment (.venv)...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Gagal membuat virtual environment!
        pause
        exit /b 1
    )
    echo     .venv berhasil dibuat.
) else (
    echo [2/3] Virtual environment (.venv) sudah tersedia.
)
echo.

:: 3. Upgrade pip dan instal dependensi
echo [3/3] Menginstal dan memperbarui dependensi (PySide6, OpenCV, NumPy)...
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Terjadi kesalahan saat mengunduh paket dependensi.
    echo Pastikan komputer terhubung ke internet dan coba kembali.
    pause
    exit /b 1
)

echo.
echo ========================================================
echo          Instalasi Selesai & Siap Digunakan!
echo ========================================================
echo.
echo Cara menjalankan aplikasi:
echo   - Klik 2x "run.bat"      : Pemantauan kamera live normal
echo   - Klik 2x "run_mock.bat" : Mode simulasi (tanpa kamera fisik)
echo   - Klik 2x "build.bat"    : Kompilasi menjadi file ManyPlayer.exe
echo.
pause
