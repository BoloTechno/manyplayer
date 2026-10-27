#!/usr/bin/env bash
set -e

# ========================================================
#       ManyPlayer - Mode Simulasi CCTV (--mock)
#              Skrip Peluncuran Linux
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

echo "========================================================"
echo "          ManyPlayer - Mode Simulasi (--mock)           "
echo "   Menghasilkan feed kamera sintetis untuk pengujian    "
echo "========================================================"
echo ""

exec .venv/bin/python src/main.py --mock "$@"
