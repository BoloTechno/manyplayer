# ManyPlayer - Windows CCTV Video Wall & AI People Counter

Aplikasi desktop Windows mandiri (*standalone*) berbasis **Lean Clean Architecture** untuk pemantauan multi-kamera CCTV (RTSP) skala besar dan analitik penghitung orang lewat (*people counter*) cerdas langsung di layar.

---

## 🌟 Fitur Utama

### 1. Menu 1: Multi-Grid Monitor (16, 25, dan 36 Kamera)
* **Pengalihan Grid Cepat**: Tombol saklar instan untuk mode **4x4 (16 Kamera)**, **5x5 (25 Kamera)**, dan **6x6 (36 Kamera)**.
* **Pull-Based Master UI Timer (15 FPS)**: Menggunakan satu timer render terpusat untuk menarik frame gambar, mencegah *UI freeze* (menghilangkan bottleneck 500+ sinyal Qt per detik).
* **Dynamic Stream Throttling**: Otomatis mematikan thread koneksi kamera yang tidak terlihat (misal: saat mode 16 kamera aktif, kamera 17–36 tidak memakan CPU).
* **Anti-Hang RTSP Socket Timeout**: Konfigurasi TCP dan timeout socket 5 detik (`stimeout=5000000`). Jika kamera dicabut/mati, aplikasi mendeteksi dalam 5 detik tanpa membeku saat ditutup.

### 2. Menu 2: AI People Counter (Analitik 1 atau 2 Kamera)
* **Pilihan Tampilan**: Mode 1 Kamera (Layar Penuh Terfokus) atau 2 Kamera (Split Screen Kiri & Kanan).
* **On-Screen Display (HUD)**: Panel semi-transparan angka kontras tinggi di layar:
  * 🟢 **MASUK (IN)**: Jumlah orang yang masuk melintasi garis.
  * 🔴 **KELUAR (OUT)**: Jumlah orang yang keluar melintasi garis.
  * 🔵 **DI DALAM**: Selisih bersih orang saat ini (*Masuk - Keluar*).
* **Finite Line Segment Crossing**: Menggunakan algoritma *Counter-Clockwise (CCW) Segment Intersection* berhingga. Orang yang berjalan di luar kusen pintu tidak akan memicu hitungan palsu.
* **Debounce State Memory**: Mencegah satu orang yang berdiri di sekitar garis dihitung berulang kali.
* **Tombol Reset Instan**: Tombol `"🔄 Reset Angka Counter"` untuk mengembalikan angka ke 0 kapan saja.

### 3. Resource Decoupling
* Saat berada di **Menu 1 (Grid)**, mesin AI berada dalam status **PAUSE (0% beban AI)**.
* Saat berada di **Menu 2 (Counter)**, thread grid 36 kamera dihentikan sementara agar seluruh daya fokus pada deteksi akurat 1–2 kamera.

---

## 📁 Struktur Konfigurasi Kamera

Alamat RTSP disimpan di file teks [`config/cameras.json`](file:///home/tipol/Projects/manyplayer/config/cameras.json). Pengguna dapat mengubah nama atau alamat IP kamera kapan saja menggunakan Notepad:

```json
[
  {
    "id": 1,
    "name": "01 - Pintu Masuk Utama",
    "sub_stream_url": "rtsp://admin:pass@192.168.1.101:554/stream2",
    "main_stream_url": "rtsp://admin:pass@192.168.1.101:554/stream1",
    "is_counter_target": "Cam 1"
  },
  {
    "id": 2,
    "name": "02 - Pintu Keluar Belakang",
    "sub_stream_url": "rtsp://admin:pass@192.168.1.102:554/stream2",
    "main_stream_url": "rtsp://admin:pass@192.168.1.102:554/stream1",
    "is_counter_target": "Cam 2"
  }
]
```

---

## 🚀 Menjalankan Aplikasi

### Persyaratan Lingkungan:
* Windows 10 / 11 (64-bit)
* Python 3.10+ (atau gunakan file `.exe` hasil build)

### Menjalankan dari Source Code:
```bash
# 1. Install dependensi
pip install -r requirements.txt

# 2. Jalankan aplikasi
python src/main.py
```

### Menjalankan Pengujian Otomatis (Unit Tests):
```bash
PYTHONPATH=. pytest tests/unit/ -v
```

---

## 📦 Kompilasi ke Windows Standalone (.exe)

Untuk membuat file executable mandiri yang tinggal didobel-klik di Windows tanpa instalasi Python:

```bash
pip install pyinstaller
pyinstaller build_windows.spec
```
File executable siap pakai akan berada di dalam folder `dist/ManyPlayer/ManyPlayer.exe`.
