# ManyPlayer - Ultra-Lightweight RTSP Multi-Camera Surveillance Wall

Aplikasi desktop Windows mandiri (*standalone*) berbasis **Lean Clean Architecture** untuk pemantauan multi-kamera CCTV (RTSP) skala besar (hingga 36 kamera secara simultan) dengan latensi mendekati nol, konsumsi daya rendah, dan antarmuka modern yang responsif.

---

## 🌟 Fitur Utama

* **Grid Monitoring Skalabel**:
  * Pengalihan tata letak instan: **4x4 (16 Kamera)**, **5x5 (25 Kamera)**, dan **6x6 (36 Kamera)**.
  * **Mode Fokus 1x1**: Klik dua kali pada kamera mana pun untuk memperbesar ke layar penuh terfokus.
  * **Mode Layar Penuh (F11)**: Sembunyikan window border dan taskbar untuk pengalaman CCTV video wall murni.
* **Header Terpadu Satu Baris (*Unified Top Header*)**:
  * Seluruh kontrol esensial (status koneksi, Play/Stop semua kamera, tombol switch layout, aspek rasio, OSD kamera, tombol Kelola Kamera, dan Fullscreen) terintegrasi rapi dalam satu bilah toolbar atas.
* **Performa Tinggi & Anti-Freeze**:
  * **Pull-Based Master UI Timer (15 FPS)**: Menggunakan satu timer terpusat untuk me-render gambar, mengeliminasi bottleneck ratusan sinyal Qt per detik.
  * **Dynamic Stream Throttling**: Otomatis menghentikan koneksi kamera yang sedang tidak terlihat di layar untuk menghemat bandwidth jaringan dan CPU.
  * **Stream Deduplication / Fan-out**: Jika beberapa slot menampilkan URL RTSP yang sama, aplikasi hanya membuka 1 koneksi fisik ke kamera dan membagikan frame-nya secara instan.
  * **Zero Latency LIFO Frame Buffer**: Frame diproses langsung dari soket tanpa antrean buffer yang menyebabkan video delay/terlambat.
* **Kompatibilitas Luas & In-Process RTSP Bridge**:
  * Menggunakan TCP transport untuk mencegah artefak gambar abu-abu (*grey screen*).
  * Dilengkapi proxy TCP loopback internal yang otomatis membersihkan dual-auth challenge SHA-256 pada kamera modern (seperti Hikvision/Dahua) sehingga dapat di-demux oleh FFmpeg secara mulus tanpa konfigurasi tambahan.
* **Interaktivitas Cepat**:
  * **Drag & Drop Slot Swapping**: Seret dan letakkan kartu kamera untuk menukar posisi tampilan tanpa memutuskan koneksi streaming.
  * **Pengaturan Rasio Aspek Fleksibel**: Pilihan mode **Auto**, **16:9**, **4:3**, atau **Stretch** dengan letterboxing/pillarboxing otomatis.
  * **Dialog Kelola Kamera Responsif**: Kelola daftar kamera dengan live search, duplikasi baris, uji koneksi langsung dengan snapshot preview, dan live reload tanpa restart.

---

## 📁 Struktur Konfigurasi Kamera

Alamat RTSP disimpan pada berkas JSON [`config/cameras.json`](file:///home/tipol/Projects/manyplayer/config/cameras.json). Anda dapat mengeditnya langsung menggunakan Notepad atau melalui tombol **`[ ⚙️ Kelola Kamera ]`** di aplikasi:

```json
[
  {
    "id": 1,
    "name": "01 - Pintu Masuk Utama",
    "stream_url": "rtsp://admin:password123@192.168.1.101:554/Streaming/Channels/102"
  },
  {
    "id": 2,
    "name": "02 - Area Parkir Barat",
    "stream_url": "rtsp://admin:password123@192.168.1.102:554/Streaming/Channels/102"
  }
]
```

---

## 🚀 Penggunaan Cepat

ManyPlayer menyediakan skrip otomatis sekali klik / sekali eksekusi di dalam folder `scripts/`:

### A. Pengguna Windows (`scripts\windows\`)
* **Instalasi Dependensi**: Buka folder `scripts\windows\` dan klik ganda **`install.bat`**
* **Menjalankan Live CCTV**: Klik ganda **`run.bat`**
* **Mode Simulasi / Demo**: Klik ganda **`run_mock.bat`**
* **Kompilasi ke `.exe`**: Klik ganda **`build.bat`** (hasil di `dist\ManyPlayer\ManyPlayer.exe`)
* 📖 *Panduan Lengkap Windows*: [**`DOCS/PANDUAN_WINDOWS.md`**](file:///home/tipol/Projects/manyplayer/DOCS/PANDUAN_WINDOWS.md)

### B. Pengguna Linux (`scripts/linux/`)
* **Beri Izin Eksekusi** (sekali saja): `chmod +x scripts/linux/*.sh`
* **Instalasi Dependensi**: `./scripts/linux/install.sh`
* **Menjalankan Live CCTV**: `./scripts/linux/run.sh`
* **Mode Simulasi / Demo**: `./scripts/linux/run_mock.sh`
* **Kompilasi Standalone Binary**: `./scripts/linux/build.sh` (hasil di `dist/ManyPlayer/ManyPlayer`)
* **Desktop Launcher**: Tersedia file [`scripts/linux/manyplayer.desktop`](file:///home/tipol/Projects/manyplayer/scripts/linux/manyplayer.desktop) untuk integrasi Application Menu / Dock Linux.
* 📖 *Panduan Lengkap Linux*: [**`DOCS/PANDUAN_LINUX.md`**](file:///home/tipol/Projects/manyplayer/DOCS/PANDUAN_LINUX.md)

---

## 💻 Penggunaan Manual via Baris Perintah (CMD / PowerShell / Bash)

### Persyaratan Sistem:
* Windows 10 / 11 (64-bit) atau Linux
* Python 3.10+

```bash
# 1. Siapkan virtual environment
python -m venv .venv

# 2. Aktifkan venv
# Di Windows:
.venv\Scripts\activate
# Di Linux:
source .venv/bin/activate

# 3. Pasang dependensi
pip install -r requirements.txt

# 4. Jalankan aplikasi
python src/main.py

# Menjalankan dalam mode simulasi offline:
python src/main.py --mock
```

### Menjalankan Pengujian Unit Otomatis (Unit Tests):
```bash
pytest
```
Semua 62 unit tests terverifikasi lolos 100%.

---

## 📄 Lisensi
Didistribusikan untuk keperluan operasional sistem pengawasan CCTV mandiri.
