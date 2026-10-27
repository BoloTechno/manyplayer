#!/usr/bin/env bash
set -e

# ========================================================
#       ManyPlayer - CCTV Multi-Camera Video Wall
#            Kompilasi Standalone Binary Linux
# ========================================================

# Berpindah ke root direktori proyek
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f ".venv/bin/python" ]; then
    echo "[PERINGATAN] Virtual environment belum terpasang!"
    echo "Menjalankan instalasi otomatis terlebih dahulu..."
    echo ""
    "$ROOT_DIR/scripts/linux/install.sh"
fi

echo "[1/2] Memastikan PyInstaller terpasang di .venv..."
.venv/bin/python -m pip install "pyinstaller>=6.0.0"
echo ""

echo "[2/2] Memulai kompilasi dengan PyInstaller (build_windows.spec)..."
.venv/bin/pyinstaller build_windows.spec

echo ""
echo "========================================================"
echo "                 Kompilasi Sukses!                      "
echo "========================================================"
echo ""
echo "File binary mandiri Linux siap pakai tersedia di:"
echo "$ROOT_DIR/dist/ManyPlayer/ManyPlayer"
echo ""
echo "Anda dapat menjalankan aplikasi hasil build dengan:"
echo "./dist/ManyPlayer/ManyPlayer"
echo ""
