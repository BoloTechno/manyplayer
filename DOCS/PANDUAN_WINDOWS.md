# PANDUAN LENGKAP PENGGUNAAN & INSTALASI WINDOWS
## ManyPlayer - Ultra-Lightweight RTSP Multi-Camera Surveillance Wall

Dokumen ini berisi panduan langkah-demi-langkah bagi administrator dan operator CCTV untuk memasang, mengonfigurasi, dan mengoperasikan ManyPlayer pada sistem operasi **Microsoft Windows 10 dan Windows 11 (64-bit)**.

---

## 1. Persyaratan Sistem & Perangkat Keras

| Komponen | Spesifikasi Minimum (16 Kamera) | Spesifikasi Rekomendasi (36 Kamera) |
| :--- | :--- | :--- |
| **Sistem Operasi** | Windows 10 / 11 Home/Pro (64-bit) | Windows 10 / 11 Pro (64-bit) |
| **Prosesor (CPU)** | Intel Core i3 Gen 6 / AMD Ryzen 3 | Intel Core i5/i7 Gen 8+ / AMD Ryzen 5+ |
| **Memori (RAM)** | 4 GB RAM | 8 GB – 16 GB RAM |
| **Kartu Grafis** | Intel HD Graphics terintegrasi | GPU terintegrasi modern atau diskrit |
| **Koneksi Jaringan** | Fast Ethernet (100 Mbps) | Gigabit Ethernet (1000 Mbps) kabel LAN |
| **Resolusi Layar** | 1366 x 768 piksel | 1920 x 1080 (Full HD) atau 4K Ultra HD |

> [!TIP]
> Untuk pemantauan 16–36 kamera secara simultan, **sangat disarankan menggunakan koneksi kabel LAN (Ethernet)** daripada Wi-Fi guna mencegah paket data video hilang (*packet drop*) dan layar abu-abu (*grey screen*).

---

## 2. Cara Cepat: Menjalankan Menggunakan Skrip Otomatis (.bat)

Jika Anda memiliki kode sumber ManyPlayer dan ingin menjalankannya di Windows:

### Langkah 1: Pasang Python (Hanya Perlu Dilakukan Sekali)
1. Kunjungi situs resmi Python: [https://www.python.org/downloads/](https://www.python.org/downloads/).
2. Unduh installer **Python 3.10, 3.11, atau 3.12** untuk Windows (64-bit).
3. Jalankan file instalasi `.exe`.
4. **PENTING**: Pada layar pertama instalasi, centang kotak pilihan:  
   ☑ **`Add python.exe to PATH`** (atau *"Add Python to environment variables"*).
5. Klik **Install Now** dan tunggu hingga selesai.

### Langkah 2: Jalankan `install.bat`
1. Buka folder proyek `manyplayer`.
2. Klik ganda pada file **`install.bat`**.
3. Jendela Command Prompt akan muncul dan otomatis:
   - Membuat lingkungan terisolasi virtual environment (`.venv`).
   - Memperbarui sistem manajemen paket (`pip`).
   - Mengunduh dan memasang modul tampilan (PySide6) dan pemroses video (OpenCV & NumPy).
4. Setelah muncul tulisan `Instalasi Selesai & Siap Digunakan!`, tekan sembarang tombol untuk menutup jendela.

### Langkah 3: Buka Aplikasi
* **Untuk Penggunaan CCTV Nyata**:  
  Klik ganda **`run.bat`**. Aplikasi akan langsung terbuka dalam mode pemantauan kamera.
* **Untuk Pengujian / Demo (Tanpa CCTV Fisik)**:  
  Klik ganda **`run_mock.bat`**. Aplikasi akan memutar siaran kamera simulasi sintetis lokal.

---

## 3. Cara Portable: Kompilasi Menjadi File `.exe` Standalone

Anda dapat membuat aplikasi dalam bentuk file executable tunggal yang dapat dipindahkan ke komputer Windows lain (misal: komputer pos keamanan atau ruang kontrol) **tanpa perlu menginstal Python**.

### Cara Membuat File `.exe`:
1. Klik ganda pada file **`build.bat`**.
2. Skrip akan memasang PyInstaller dan mengompilasi program secara otomatis.
3. Setelah selesai, folder hasil build mandiri akan berada di:
   ```text
   manyplayer\dist\ManyPlayer\
   ```
4. Di dalam folder tersebut terdapat file utama:
   ```text
   ManyPlayer.exe
   ```

### Cara Mendistribusikan ke Komputer Lain:
1. Salin seluruh isi folder `dist\ManyPlayer` (atau kompres menjadi file `.zip`).
2. Pindahkan folder tersebut ke PC target (misal ke `C:\Program Files\ManyPlayer` atau Desktop).
3. Pengguna di PC target cukup mengeklik ganda file **`ManyPlayer.exe`**.

---

## 4. Panduan Format URL RTSP Kamera CCTV

ManyPlayer mendukung protokol standar industri **RTSP (Real-Time Streaming Protocol)** over TCP. Format umum alamat stream adalah:

```text
rtsp://[username]:[password]@[IP_Address]:[Port]/[Path]
```

Berikut contoh URL RTSP resmi dari merk CCTV populer:

### 1. Hikvision & Hilook
* **Sub-stream (Rekomendasi untuk Grid multi-kamera)**:
  ```text
  rtsp://admin:password123@192.168.1.101:554/Streaming/Channels/102
  ```
* **Main-stream (Resolusi tinggi)**:
  ```text
  rtsp://admin:password123@192.168.1.101:554/Streaming/Channels/101
  ```
*(Angka `102` berarti Kamera 1, Stream 2. Untuk Kamera 2 gunakan `202`, Kamera 3 gunakan `302`, dst.)*

> [!NOTE]
> Kamera Hikvision modern sering mengirimkan tantangan otentikasi ganda (MD5 dan SHA-256). ManyPlayer telah dilengkapi fitur *In-Process RTSP Bridge* loopback internal yang otomatis membersihkan otentikasi SHA-256 sehingga kamera Hikvision langsung terhubung mulus tanpa error 401.

### 2. Dahua & Imou
* **Sub-stream**:
  ```text
  rtsp://admin:password123@192.168.1.102:554/cam/realmonitor?channel=1&subtype=1
  ```
* **Main-stream**:
  ```text
  rtsp://admin:password123@192.168.1.102:554/cam/realmonitor?channel=1&subtype=0
  ```

### 3. Uniview (UNV)
* **Sub-stream**:
  ```text
  rtsp://admin:password123@192.168.1.103:554/unicast/c1/s1/live
  ```
* **Main-stream**:
  ```text
  rtsp://admin:password123@192.168.1.103:554/unicast/c1/s0/live
  ```

### 4. TP-Link Tapo
* **Sub-stream (Stream 2)**:
  ```text
  rtsp://admin:password123@192.168.1.104:554/stream2
  ```
* **Main-stream (Stream 1)**:
  ```text
  rtsp://admin:password123@192.168.1.104:554/stream1
  ```

### 5. SPC / XM / Xiongmai (Generic IP Cam)
```text
rtsp://admin:password123@192.168.1.105:554/user=admin_password=password123_channel=1_stream=1.sdp
```

---

## 5. Cara Mengonfigurasi Daftar Kamera

Tersedia dua cara mudah untuk mengatur kamera:

### Opsi A: Lewat Tombol `[ ⚙️ Kelola Kamera ]` di Aplikasi (Rekomendasi)
1. Buka aplikasi ManyPlayer.
2. Pada bilah atas (header), klik tombol **`[ ⚙️ Kelola Kamera ]`**.
3. Kotak dialog konfigurasi akan terbuka:
   * **Tambah Kamera Baru**: Klik tombol **`[ ➕ Tambah Kamera ]`**.
   * **Edit Alamat RTSP**: Dobel klik pada sel *Alamat RTSP Stream URL* dan paste alamat RTSP kamera Anda.
   * **Uji Koneksi Kamera**: Klik tombol **`[ ⚡ Uji ]`** pada baris kamera. Sistem akan mencoba terhubung dan menampilkan jendela snapshot preview serta resolusi video secara real-time.
   * **Duplikasi Baris**: Klik baris kamera lalu tekan **`[ 📋 Duplikasi ]`** untuk mempercepat input kamera dengan IP berurutan.
   * **Simpan**: Klik tombol **`[ 💾 Simpan & Terapkan ]`**. Grid akan langsung memuat konfigurasi baru tanpa perlu merestart aplikasi!

### Opsi B: Lewat File `config/cameras.json` (Menggunakan Notepad)
1. Buka folder `config` di dalam direktori aplikasi.
2. Klik kanan pada file **`cameras.json`** -> pilih **Open with Notepad**.
3. Sesuaikan `id`, `name`, dan `stream_url`:
   ```json
   [
     {
       "id": 1,
       "name": "Pintu Masuk",
       "stream_url": "rtsp://admin:pass@192.168.1.101:554/stream2"
     },
     {
       "id": 2,
       "name": "Lobi Utama",
       "stream_url": "rtsp://admin:pass@192.168.1.102:554/stream2"
     }
   ]
   ```
4. Simpan file (`Ctrl + S`).

---

## 6. Panduan Penggunaan Antarmuka & Pintasan Keyboard

* **Mengubah Jumlah Tampilan Grid**:
  * Klik tombol **`[ 4x4 (16) ]`** untuk menampilkan 16 kamera.
  * Klik tombol **`[ 5x5 (25) ]`** untuk menampilkan 25 kamera.
  * Klik tombol **`[ 6x6 (36) ]`** untuk menampilkan 36 kamera.
* **Mode Fokus 1x1 (Perbesar Satu Kamera)**:
  * Dobel klik pada kotak kamera mana saja untuk memperbesar kamera tersebut ke mode fokus 1x1.
  * Untuk kembali ke mode multi-grid, klik tombol **`[ ⬅ Kembali ke Grid ]`** di bilah atas.
* **Mode Layar Penuh (Fullscreen Video Wall)**:
  * Tekan tombol **`F11`** pada keyboard atau klik tombol **`[ ⛶ Fullscreen ]`**.
  * Judul jendela dan taskbar Windows akan disembunyikan.
  * Tekan **`Esc`** atau **`F11`** kembali untuk keluar dari mode layar penuh.
* **Menukar Posisi Kamera (Drag & Drop)**:
  * Klik dan tahan kartu kamera yang ingin dipindahkan.
  * Seret (*drag*) ke slot kamera tujuan lalu lepaskan (*drop*).
  * Posisi kamera langsung tertukar tanpa memutuskan atau me-restart stream video.
* **Menghidupkan / Mematikan Stream per Kamera**:
  * Arahkan kursor mouse ke pojok kanan atas kartu kamera.
  * Klik ikon tombol putar/jeda (▶ / ⏸) untuk menghentikan feed kamera tersebut secara individual tanpa memengaruhi kamera lainnya.
* **Pengaturan Rasio Layar**:
  * Pilih pada menu dropdown rasio di header:
    * **Auto**: Mempertahankan rasio alami feed video asli.
    * **16:9**: Format standar kamera HD modern (menggunakan letterboxing/pillarboxing hitam yang rapi, tanpa distorsi gepeng).
    * **4:3**: Format standar CCTV resolusi VGA / legacy.
    * **Penuh (Stretch)**: Meregangkan video memenuhi seluruh kotak slot.

---

## 7. Pemecahan Masalah (Troubleshooting Windows)

### 1. Peringatan "Windows protected your PC" (Microsoft Defender SmartScreen)
* **Penyebab**: File `.exe` yang baru dikompilasi secara lokal belum memiliki sertifikat tanda tangan digital komersial (*code-signing certificate*).
* **Solusi**:
  1. Klik teks tautan **`More info`** (*Informasi selengkapnya*).
  2. Klik tombol **`Run anyway`** (*Tetap jalankan*).
  3. Aplikasi akan berjalan normal.

### 2. Kamera Berstatus "OFFLINE" atau "Koneksi Timeout"
* **Langkah Pengecekan**:
  1. Pastikan PC dan kamera berada dalam satu subnet jaringan IP yang sama (misal PC IP: `192.168.1.50`, kamera: `192.168.1.101`).
  2. Buka Command Prompt di Windows, lalu uji koneksi dasar dengan perintah ping:
     ```cmd
     ping 192.168.1.101
     ```
  3. Pastikan username dan password di URL RTSP sudah benar. Jika password mengandung karakter khusus (seperti `@`, `:`, atau `/`), gantikan dengan format *URL encode* (misal karakter `@` diganti dengan `%40`).
  4. Periksa apakah port RTSP `554` terbuka di router atau switch jaringan Anda.

### 3. Peringatan Windows Defender Firewall
* Saat pertama kali dijalankan, Windows mungkin menampilkan dialog:  
  *"Windows Defender Firewall has blocked some features of this app"*.
* **Solusi**:  
  Centang kotak **`Private networks`** (Jaringan privat/rumah/kantor) lalu klik **`Allow access`** agar aplikasi dapat menerima paket video RTSP melalui jaringan lokal.

### 4. Gambar Video Pecah / Abu-Abu (Grey Screen)
* ManyPlayer secara default telah mengunci mode transmisi ke **RTSP over TCP** (`rtsp_transport;tcp`).
* Jika gambar tetap abu-abu, hal ini biasanya disebabkan oleh kabel jaringan yang longgar, switch jaringan yang kelebihan beban (over-capacity), atau bandwidth kamera (bitrate) yang disetel terlalu tinggi pada NVR/kamera. Coba turunkan bitrate sub-stream kamera di pengaturan web kamera ke kisaran 512 Kbps – 1024 Kbps per feed.
