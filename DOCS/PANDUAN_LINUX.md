# PANDUAN LENGKAP PENGGUNAAN & INSTALASI LINUX
## ManyPlayer - Ultra-Lightweight RTSP Multi-Camera Surveillance Wall

Dokumen ini berisi panduan lengkap langkah-demi-langkah bagi administrator dan operator untuk memasang, mengonfigurasi, dan mengoperasikan ManyPlayer pada berbagai distribusi **Linux (Ubuntu, Debian, Linux Mint, Fedora, Arch Linux, dan distro turunannya)**.

---

## 1. Persyaratan Sistem & Paket Dependensi Distro

ManyPlayer menggunakan antarmuka modern berbasis **PySide6 (Qt6)** dan pemroses stream video **OpenCV**. Pastikan dependensi sistem dasar telah terpasang sesuai distribusi Linux Anda:

### A. Ubuntu / Debian / Linux Mint / Pop!_OS
Buka terminal dan jalankan perintah berikut:
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip libgl1 libegl1 libglib2.0-0 libxcb-xinerama0 libxcb-cursor0
```

### B. Fedora / RHEL / CentOS Stream
```bash
sudo dnf install -y python3 python3-pip mesa-libGL mesa-libEGL glib2 libxcb
```

### C. Arch Linux / Manjaro / EndeavourOS
```bash
sudo pacman -S --needed python python-pip mesa libglvnd glib2
```

---

## 2. Cara Cepat: Menggunakan Skrip Otomasi Shell (.sh)

ManyPlayer menyediakan skrip shell otomatis yang telah disesuaikan untuk lingkungan Linux di dalam folder `scripts/linux/`:

### Langkah 1: Berikan Izin Eksekusi (Hanya Sekali)
Buka terminal di dalam folder proyek ManyPlayer dan pastikan seluruh skrip memiliki izin eksekusi:
```bash
chmod +x scripts/linux/*.sh
```

### Langkah 2: Jalankan Instalasi Otomatis
```bash
./scripts/linux/install.sh
```
Skrip ini akan secara otomatis:
- Memeriksa Python 3 di sistem Anda.
- Membuat lingkungan virtual terisolasi (`.venv`).
- Memperbarui `pip` dan memasang pustaka resmi (`PySide6`, `OpenCV`, `NumPy`, `pytest`).

### Langkah 3: Menjalankan Aplikasi
* **Mode Pemantauan CCTV Nyata**:
  ```bash
  ./scripts/linux/run.sh
  ```
* **Mode Simulasi / Demo (Tanpa CCTV Fisik)**:
  ```bash
  ./scripts/linux/run_mock.sh
  ```

---

## 3. Kompilasi Menjadi File Standalone Linux Executable

Anda dapat mengompilasi ManyPlayer menjadi binary mandiri (ELF executable) yang dapat dijalankan tanpa memerlukan dependensi Python lokal:

```bash
./scripts/linux/build.sh
```

Hasil kompilasi akan berada di folder:
```text
dist/ManyPlayer/ManyPlayer
```

Anda dapat menjalankan binary tersebut langsung dengan perintah:
```bash
./dist/ManyPlayer/ManyPlayer
```

---

## 4. Integrasi Menu Aplikasi & Desktop Shortcut (Freedesktop)

Agar ManyPlayer muncul pada menu aplikasi sistem (seperti GNOME App Grid, KDE Kickoff, atau XFCE Whisker Menu), Anda dapat memasangnya secara otomatis atau manual:

### Cara Otomatis (Direkomendasikan):
Jalankan skrip instalasi dengan opsi `--desktop`:
```bash
./scripts/linux/install.sh --desktop
```

### Cara Manual:
```bash
# 1. Pastikan folder aplikasi lokal tersedia
mkdir -p ~/.local/share/applications

# 2. Salin file desktop entry ke direktori aplikasi pengguna
cp scripts/linux/manyplayer.desktop ~/.local/share/applications/

# 3. Perbarui path eksekusi ke direktori absolut proyek Anda
PROJECT_PATH=$(pwd)
sed -i "s|cd '%k/../..'|cd '$PROJECT_PATH'|g" ~/.local/share/applications/manyplayer.desktop

# 4. Berikan izin eksekusi pada file desktop
chmod +x ~/.local/share/applications/manyplayer.desktop
```
Ikon ManyPlayer sekarang akan langsung muncul di daftar aplikasi sistem dan dapat di-*pin* ke dock favorit Anda.

---

## 5. Pengaturan Display Server: Wayland vs X11

ManyPlayer (melalui Qt6/PySide6) mendukung protokol grafis modern **Wayland** maupun **X11 (X.Org)** secara native.

### Rekomendasi Driver & Display:
* **Intel / AMD GPU**: Secara default berjalan sangat lancar dan mulus di Wayland maupun X11.
* **NVIDIA Proprietary Driver**: Jika Anda menggunakan driver proprietary NVIDIA pada Wayland dan mengalami kendala seperti *window flickering* atau *scaling*, Anda dapat memaksa aplikasi berjalan di lapisan kompatibilitas XWayland (X11) dengan menambahkan variabel lingkungan `QT_QPA_PLATFORM=xcb`:

```bash
QT_QPA_PLATFORM=xcb ./scripts/linux/run.sh
```

---

## 6. Setup Mode Kiosk CCTV 24/7 (Dedicated Surveillance Display)

Jika komputer Linux Anda difungsikan sebagai monitor CCTV permanen yang harus menyala 24 jam nonstop tanpa campur tangan pengguna:

### A. Autostart Saat Komputer Dinyalakan (User Login)
Buat konfigurasi autostart agar ManyPlayer langsung terbuka saat desktop Linux login:
```bash
mkdir -p ~/.config/autostart
cp ~/.local/share/applications/manyplayer.desktop ~/.config/autostart/
```

### B. Menonaktifkan Layar Mati / Screen Sleep (DPMS)
Agar layar monitor CCTV tidak mati atau masuk mode hemat daya (*blank screen*):
* **Pada X11**:
  Tambahkan perintah ini ke `~/.xprofile` atau jalankan di terminal:
  ```bash
  xset s off -dpms
  ```
* **Pada GNOME Desktop (Wayland/X11)**:
  ```bash
  gsettings set org.gnome.desktop.session idle-delay 0
  gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing'
  ```

---

## 7. Pengaturan Firewall Jaringan (RTSP Port 554)

Secara default, paket video RTSP ditarik oleh ManyPlayer melalui koneksi keluar (*outgoing* TCP). Namun jika sistem Linux Anda menerapkan aturan firewall ketat untuk komunikasi antar-VLAN CCTV:

### UFW (Ubuntu / Debian / Linux Mint)
```bash
# Izinkan lalu lintas RTSP
sudo ufw allow out 554/tcp
sudo ufw allow in 554/tcp
sudo ufw status
```

### Firewalld (Fedora / RHEL / CentOS)
```bash
sudo firewall-cmd --add-port=554/tcp --permanent
sudo firewall-cmd --reload
```

---

## 8. Panduan Konfigurasi Kamera RTSP

Konfigurasi daftar kamera disimpan dalam file JSON [`config/cameras.json`](file:///home/tipol/Projects/manyplayer/config/cameras.json):

```json
[
  {
    "id": 1,
    "name": "01 - Gerbang Depan",
    "stream_url": "rtsp://admin:pass123@192.168.1.101:554/Streaming/Channels/102"
  },
  {
    "id": 2,
    "name": "02 - Lobi Kantor",
    "stream_url": "rtsp://admin:pass123@192.168.1.102:554/cam/realmonitor?channel=1&subtype=1"
  }
]
```

> [!TIP]
> Anda juga dapat mengubah URL, menambah kamera, serta menguji koneksi langsung (*Live Test & Snapshot Preview*) melalui tombol **`[ ⚙️ Kelola Kamera ]`** pada antarmuka aplikasi.

---

## 9. Pemecahan Masalah (Troubleshooting Linux)

### 1. Error: `qt.qpa.plugin: Could not load the Qt platform plugin "xcb"`
* **Penyebab**: Pustaka XCB sistem belum lengkap.
* **Solusi**: Pasang paket dependensi XCB tambahan:
  * Ubuntu/Debian: `sudo apt install -y libxcb-cursor0 libxcb-xinerama0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0`
  * Fedora: `sudo dnf install -y xcb-util-cursor xcb-util-image xcb-util-keysyms xcb-util-wm`

### 2. Error: `Permission denied` Saat Menjalankan Skrip `.sh`
* **Solusi**: Berikan izin eksekusi pada skrip:
  ```bash
  chmod +x *.sh
  ```

### 3. Kamera Hikvision Error 401 Unauthorized
* ManyPlayer memiliki fitur internal *In-Process RTSP Bridge* loopback yang otomatis menanggalkan otentikasi SHA-256 yang tidak didukung demuxer FFmpeg. Pastikan alamat IP kamera dapat di-ping dari terminal:
  ```bash
  ping -c 3 192.168.1.101
  ```
