#!/usr/bin/env bash
set -e

# ========================================================
#        ManyPlayer - CCTV Multi-Camera Video Wall
#            Instalasi Otomatis untuk Linux
# ========================================================

# Berpindah ke root direktori proyek
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "========================================================"
echo "       ManyPlayer - CCTV Multi-Camera Video Wall        "
echo "           Instalasi Otomatis untuk Linux               "
echo "========================================================"
echo ""

# 1. Periksa ketersediaan Python 3 di sistem
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] Python 3 tidak ditemukan di sistem Linux Anda!"
    echo "Silakan instal Python 3 terlebih dahulu:"
    echo "  - Ubuntu/Debian : sudo apt install python3 python3-venv python3-pip"
    echo "  - Fedora/RHEL   : sudo dnf install python3 python3-pip"
    echo "  - Arch Linux    : sudo pacman -S python python-pip"
    exit 1
fi

echo "[1/3] Python terdeteksi di sistem:"
python3 --version
echo ""

# 2. Siapkan Virtual Environment (.venv)
if [ ! -f ".venv/bin/python" ]; then
    echo "[2/3] Membuat virtual environment (.venv)..."
    if ! python3 -m venv .venv 2>/dev/null; then
        echo "[ERROR] Gagal membuat virtual environment!"
        echo "Pastikan paket python3-venv terpasang di sistem Anda:"
        echo "  - Ubuntu/Debian : sudo apt install python3-venv"
        echo "  - Fedora/RHEL   : sudo dnf install python3-libs"
        echo "  - Arch Linux    : sudo pacman -S python"
        exit 1
    fi
    echo "    .venv berhasil dibuat."
else
    echo "[2/3] Virtual environment (.venv) sudah tersedia."
fi

# Buat symlink kemudahan agar perintah `venv/bin/python` maupun `.venv/bin/python` bekerja
ln -sf .venv venv
echo ""

# 3. Upgrade pip dan instal dependensi
echo "[3/3] Menginstal dan memperbarui dependensi (PySide6, OpenCV, NumPy)..."
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

# 4. Opsional: Pasang shortcut desktop aplikasi jika opsi --desktop diberikan
if [ "$1" = "--desktop" ] || [ "$2" = "--desktop" ]; then
    echo ""
    echo "Memasang shortcut aplikasi ke menu desktop Linux (~/.local/share/applications/)..."
    DESKTOP_DIR="$HOME/.local/share/applications"
    mkdir -p "$DESKTOP_DIR"
    sed -e "s|cd '%k/../..'|cd '$ROOT_DIR'|g" -e "s|Icon=camera-video|Icon=$ROOT_DIR/assets/logo.png|g" "$ROOT_DIR/scripts/linux/manyplayer.desktop" > "$DESKTOP_DIR/manyplayer.desktop"
    chmod +x "$DESKTOP_DIR/manyplayer.desktop"
    echo "✓ Shortcut menu aplikasi berhasil dipasang di $DESKTOP_DIR/manyplayer.desktop"
fi

echo ""
echo "========================================================"
echo "          Instalasi Selesai & Siap Digunakan!           "
echo "========================================================"
echo ""
echo "Cara menjalankan aplikasi:"
echo "  - ./scripts/linux/run.sh      : Pemantauan kamera live normal"
echo "  - ./scripts/linux/run_mock.sh : Mode simulasi (tanpa kamera fisik)"
echo "  - ./scripts/linux/build.sh    : Kompilasi binary standalone dengan PyInstaller"
echo ""
echo "Tips:"
echo "  - Pasang ikon aplikasi ke menu desktop Linux (GNOME/KDE/XFCE):"
echo "    ./scripts/linux/install.sh --desktop"
echo ""
