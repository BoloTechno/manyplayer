#!/usr/bin/env bash
set -e

# ========================================================
#       ManyPlayer - CCTV Multi-Camera Video Wall
#              Skrip Peluncuran Linux
# ========================================================

# Berpindah ke root direktori proyek
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

# Periksa apakah .venv sudah terpasang
if [ ! -f ".venv/bin/python" ]; then
    echo "[PERINGATAN] Virtual environment belum terpasang!"
    echo "Menjalankan instalasi otomatis terlebih dahulu..."
    echo ""
    "$ROOT_DIR/scripts/linux/install.sh"
fi

echo "Memulai ManyPlayer Video Wall..."
exec .venv/bin/python src/main.py "$@"
