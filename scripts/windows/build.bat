@echo off
chcp 65001 >nul
title ManyPlayer - Kompilasi Windows Standalone .exe
cls

REM Beralih ke direktori utama proyek - root folder
cd /d "%~dp0..\.."

echo ========================================================
echo        ManyPlayer - CCTV Multi-Camera Video Wall
echo            Kompilasi ke Windows Standalone .exe
echo ========================================================
echo.

REM Periksa apakah .venv sudah terpasang
if exist ".venv\Scripts\python.exe" goto :start_build

echo [PERINGATAN] Virtual environment belum terpasang!
echo Menjalankan instalasi otomatis terlebih dahulu...
echo.
call "%~dp0install.bat"
if not exist ".venv\Scripts\python.exe" goto :env_failed

:start_build
echo [1/2] Memastikan PyInstaller terpasang di .venv...
.venv\Scripts\python.exe -m pip install "pyinstaller>=6.0.0"
if errorlevel 1 goto :build_failed
echo.

echo [2/2] Memulai kompilasi dengan PyInstaller...
.venv\Scripts\pyinstaller.exe build_windows.spec
if errorlevel 1 goto :build_failed

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
exit /b 0

:env_failed
echo [ERROR] Gagal menyiapkan environment. Build dibatalkan.
pause
exit /b 1

:build_failed
echo.
echo [ERROR] Kompilasi gagal! Periksa pesan error di atas.
pause
exit /b 1
