# PRODUCT REQUIREMENTS DOCUMENT (PRD)

**Nama Produk**: ManyPlayer - Windows RTSP Video Wall & On-Screen AI People Counter  
**Target Rilis**: v1.0.0  
**Target OS**: Windows 10 & Windows 11 (x64)  
**Dokumen Versi**: 1.0  
**Tanggal**: 25 Oktober 2026  
**Status**: Approved  

---

## 1. Ikhtisar Produk (Product Overview)

**ManyPlayer** adalah aplikasi desktop berbasis sistem operasi Windows yang dirancang khusus untuk memenuhi dua kebutuhan vital industri pengawasan video:
1. **Multi-Camera RTSP Monitoring**: Menampilkan pemantauan video serentak dengan opsi layout grid 16 (4x4), 25 (5x5), dan 36 (6x6) kamera.
2. **AI People Counter**: Halaman analitik terpisah untuk menghitung orang yang melintasi area pintu/koridor secara akurat pada 1 atau 2 kamera pilihan, dilengkapi indikator angka langsung di layar (*On-Screen Display / HUD*) serta tombol reset manual.

Sistem dibangun dengan arsitektur *multithreading* terisolasi untuk memastikan performa grafis mulus tanpa *UI freeze* pada lingkungan kerja Windows.

---

## 2. Arsitektur Teknis & Teknologi (Technical Architecture)

```mermaid
flowchart TD
    subgraph UI_Layer ["Lapisan Antarmuka (PySide6 / Qt GUI)"]
        MainWindow["Main Application Window"]
        Tab1["Menu Tab 1: Multi-Grid Monitor (16 / 25 / 36)"]
        Tab2["Menu Tab 2: People Counter (1 / 2 Cam Split)"]
        ConfigModal["Modal Pengaturan URL RTSP"]
    end

    subgraph Video_Pipeline ["Lapisan Pengolahan Video (OpenCV / Multi-Thread)"]
        StreamWorkerPool["RTSP Stream Worker Threads (Hingga 36 Thread Ringan)"]
        FrameBuffer["Ring Buffer / Latest Frame Buffer"]
    end

    subgraph AI_Engine ["Lapisan Analitik AI (Aktif Hanya di Tab 2)"]
        YOLO["YOLOv8n Object Detector (COCO Class: Person)"]
        Tracker["ByteTrack / Centroid Tracker (Track ID Persistence)"]
        TripwireLogic["Line Crossing Vector Math (IN / OUT Classifier)"]
    end

    ConfigJSON[("File Konfigurasi: cameras.json")] --> MainWindow
    MainWindow --> Tab1
    MainWindow --> Tab2
    MainWindow --> ConfigModal

    StreamWorkerPool --> FrameBuffer
    FrameBuffer --> Tab1
    FrameBuffer --> AI_Engine
    AI_Engine --> Tab2
```

### 2.1. Komponen Teknologi Utama
* **GUI Engine**: **PySide6 (Qt for Python)**. Menjamin rendering native Windows, manajemen memori efisien, dan layout responsif otomatis.
* **Stream Decoder**: **OpenCV (cv2) + FFmpeg backend**. Menangani protokol RTSP via TCP/UDP dengan *frame-skipping* cerdas (hanya mengambil *latest frame* agar latensi tetap 0 detik / *real-time*).
* **AI & Tracking Framework**: **Ultralytics YOLOv8n (Nano)** + **ByteTrack**. Model inferensi berbobot ringan yang sangat efisien untuk prosesor desktop modern tanpa memerlukan kartu grafis eksternal kelas industri.
* **Format Packaging**: Kompatibel untuk dibundel menggunakan **PyInstaller** menjadi distribusi `.exe` portabel untuk Windows.

---

## 3. Spesifikasi Fungsional (Functional Requirements)

### 3.1. FR-1: Manajemen Alamat Kamera (RTSP Configuration)
* **FR-1.1**: Sistem membaca konfigurasi kamera dari berkas lokal terstruktur `cameras.json`.
* **FR-1.2**: Struktur data kamera mencakup:
  * `id`: Nomor urut unik kamera (1–36).
  * `name`: Label nama lokasi (contoh: "Lobby Utama", "Parkir Barat").
  * `sub_stream_url`: URL RTSP resolusi rendah untuk menu grid (misal: 360p).
  * `main_stream_url`: URL RTSP resolusi tinggi untuk menu analitik.
  * `is_counter_target`: Penanda apakah kamera ini dialokasikan untuk analitik counter (Kamera A / Kamera B).
* **FR-1.3**: Tersedia tombol / dialog pengaturan untuk memperbarui alamat RTSP langsung dari aplikasi tanpa harus membuka teks editor secara manual.

```json
// Contoh Format cameras.json
[
  {
    "id": 1,
    "name": "Pintu Masuk Utama",
    "sub_stream_url": "rtsp://admin:pass123@192.168.1.101:554/Streaming/Channels/102",
    "main_stream_url": "rtsp://admin:pass123@192.168.1.101:554/Streaming/Channels/101",
    "is_counter_target": "Cam 1"
  },
  {
    "id": 2,
    "name": "Pintu Keluar Selatan",
    "sub_stream_url": "rtsp://admin:pass123@192.168.1.102:554/Streaming/Channels/102",
    "main_stream_url": "rtsp://admin:pass123@192.168.1.102:554/Streaming/Channels/101",
    "is_counter_target": "Cam 2"
  }
]
```

---

### 3.2. FR-2: Modul Multi-Grid Monitor (Menu 1)
* **FR-2.1 [Pengalihan Grid Dinamis & Throttling Worker]**:
  * Pilihan tombol saklar:
    * `[ 4x4 (16 Kamera) ]`: Menampilkan kamera ID 1 sampai 16. Worker kamera 17–36 wajib dimatikan (*stopped*) untuk menghemat CPU.
    * `[ 5x5 (25 Kamera) ]`: Menampilkan kamera ID 1 sampai 25. Worker kamera 26–36 dimatikan.
    * `[ 6x6 (36 Kamera) ]`: Menampilkan seluruh 36 kamera secara serentak.
* **FR-2.2 [Penyajian Video Grid via Master UI Timer]**:
  * Setiap sel grid menampilkan nama kamera di sudut kiri atas video.
  * Rasio aspek video (16:9 atau 4:3) dipertahankan agar gambar tidak terdistorsi/gepeng.
  * **Pull-Based Display**: Tampilan grid diperbarui menggunakan 1 buah *Master QTimer* terpusat pada 15 FPS yang membaca buffer gambar terbaru, bukan membanjiri antrean sinyal Qt dengan ratusan event terpisah.
* **FR-2.3 [Ketahanan Sambungan & Socket Timeout 5 Detik]**:
  * Setiap koneksi RTSP menggunakan mode TCP dengan socket timeout maksimal 5 detik (`stimeout=5000000`).
  * Jika kamera mati atau kabel terlepas, worker mendeteksi putusnya sambungan dalam waktu $\le 5$ detik tanpa membekukan aplikasi Windows (*anti-hang*).
  * Sel grid menampilkan status teks: `"Menghubungkan Ulang..."` berwarna kuning dengan latar belakang hitam, dan mencoba menyambung ulang secara berkala setiap 5 detik.
* **FR-2.4 [Isolasi Sumber Daya]**:
  * Di Menu 1 ini, model AI Object Detection berada dalam status **PAUSE / NON-AKTIF** penuh.

---

### 3.3. FR-3: Modul AI People Counter (Menu 2)
* **FR-3.1 [Pilihan Tampilan Layar]**:
  * `[ 1 Kamera (Fokus) ]`: Menampilkan 1 kamera utama yang dipilih di layar penuh.
  * `[ 2 Kamera (Split Screen) ]`: Membagi layar menjadi 2 kotak berdampingan (Kiri: Kamera 1, Kanan: Kamera 2).
* **FR-3.2 [Deteksi & Pelacakan Objek]**:
  * Menggunakan deteksi kelas `person` (manusia).
  * Algoritma tracking menetapkan ID unik pada setiap individu yang terdeteksi selama berada di dalam frame pandang kamera.
* **FR-3.3 [Garis Virtual & Logika Lintasan Segmen Berhingga (Finite Tripwire)]**:
  * Garis virtual memiliki dua titik ujung nyata: $P_1 = (x_1, y_1)$ dan $P_2 = (x_2, y_2)$ yang dapat diatur posisinya sesuai lebar kusen pintu/koridor.
  * Evaluasi lintasan menggunakan **Perpotongan Dua Segmen Garis Berhingga (CCW Intersection)** antara segmen garis virtual $(P_1, P_2)$ dan segmen langkah kaki $(C_{prev}, C_{curr})$:
    * Jika segmen langkah kaki memotong segmen garis virtual dari arah luar ke dalam $\rightarrow$ Dihitung sebagai **MASUK (+1)**.
    * Jika memotong dari arah sebaliknya $\rightarrow$ Dihitung sebagai **KELUAR (+1)**.
    * Orang yang melangkah di luar koordinat titik ujung garis (misal di samping pintu) **TIDAK AKAN** terhitung (bebas dari *false positive* garis tak hingga).
  * Dilengkapi mekanisme *debounce* berbasis riwayat ID agar satu orang yang sama tidak dihitung berulang kali saat berdiri di dekat garis.
* **FR-3.4 [On-Screen Display / HUD Statistik]**:
  * Menampilkan kotak panel angka semi-transparan dengan visibilitas tinggi di atas video:
    * 🟢 **MASUK** : `[Angka]`
    * 🔴 **KELUAR** : `[Angka]`
    * 🔵 **DI DALAM** : `[Angka (Masuk - Keluar)]`
* **FR-3.5 [Tombol Reset Manual]**:
  * Terdapat tombol jelas berlabel `"Reset Counter"` di antarmuka untuk mengembalikan seluruh angka hitungan ke angka 0 sewaktu-waktu.

---

## 4. Desain Tata Letak Antarmuka (UI Wireframes)

### 4.1. Header & Navigasi Utama
```
┌───────────────────────────────────────────────────────────────────────────────────────┐
│ [●] ManyPlayer CCTV System v1.0                     [Tab: Grid Monitor]  [Tab: Counter] │
└───────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.2. Wireframe Tab 1: Multi-Grid Monitor (Contoh Mode 4x4)
```
┌───────────────────────────────────────────────────────────────────────────────────────┐
│ Mode Grid: [ (•) 16 Kamera (4x4) ]  [ ( ) 25 Kamera (5x5) ]  [ ( ) 36 Kamera (6x6) ] │
├───────────────────┬───────────────────┬───────────────────┬───────────────────────────┤
│ [Cam 01: Pintu 1] │ [Cam 02: Pintu 2] │ [Cam 03: Koridor] │ [Cam 04: Parkir A]        │
│                   │                   │                   │                           │
├───────────────────┼───────────────────┼───────────────────┼───────────────────────────┤
│ [Cam 05: Gudang]  │ [Cam 06: Kasir]   │ [Cam 07: Tangga]  │ [Cam 08: Lobby]           │
│                   │                   │                   │                           │
├───────────────────┼───────────────────┼───────────────────┼───────────────────────────┤
│ [Cam 09: Lift]    │ [Cam 10: R.Server]│ [Cam 11: Loading] │ [Cam 12: Gerbang]         │
│                   │                   │                   │                           │
├───────────────────┼───────────────────┼───────────────────┼───────────────────────────┤
│ [Cam 13: Kantin]  │ [Cam 14: Pos Sat] │ [Cam 15: Barat]   │ [Cam 16: Timur]           │
│                   │                   │                   │                           │
└───────────────────┴───────────────────┴───────────────────┴───────────────────────────┘
```

### 4.3. Wireframe Tab 2: AI People Counter (Mode 2 Kamera Split)
```
┌───────────────────────────────────────────────────────────────────────────────────────┐
│ Tampilan: [ ( ) 1 Kamera ]  [ (•) 2 Kamera Split ]          [ 🔄 Reset Angka Counter ] │
├───────────────────────────────────────────┬───────────────────────────────────────────┤
│ KAMERA 1: Pintu Masuk Utama               │ KAMERA 2: Pintu Keluar Belakang           │
│ ┌───────────────────────────────────────┐ │ ┌───────────────────────────────────────┐ │
│ │ 🟢 MASUK: 124  🔴 KELUAR: 85          │ │ │ 🟢 MASUK: 30   🔴 KELUAR: 69          │ │
│ │ 🔵 TOTAL DI DALAM RUANGAN: 39         │ │ │ 🔵 TOTAL LOKAL: -39                   │ │
│ └───────────────────────────────────────┘ │ └───────────────────────────────────────┘ │
│                                           │                                           │
│               [ Orangnya ]                │                                           │
│  ─────────── GARIS LINTASAN ────────────  │  ─────────── GARIS LINTASAN ────────────  │
│                                           │               [ Orangnya ]                │
│                                           │                                           │
└───────────────────────────────────────────┴───────────────────────────────────────────┘
```

---

## 5. Kebutuhan Non-Fungsional (Non-Functional Requirements)

1. **Performa & Konsumsi Memori**:
   * *Buffer Dropping*: Mengingat sifat RTSP live, pemrosesan antrean frame harus mengadopsi prinsip *LIFO (Last-In-First-Out)* atau ukuran buffer maksimal 1 frame. Hal ini mencegah konsumsi memori membengkak jika komputer mengalami perlambatan sesaat.
   * *Target Frame Rate Grid & Pull Loop*: Menggunakan *Master UI Render Timer* terpusat pada 15 FPS (66ms) untuk menarik frame yang terlihat, mencegah lonjakan 500+ sinyal Qt per detik yang dapat membekukan GUI Windows.
   * *Active Stream Throttling*: Stream RTSP yang sedang tidak terlihat di mode grid yang dipilih (misal kamera 17-36 saat mode 16 kamera) wajib dihentikan untuk menghemat daya komputasi.
2. **Keandalan & Threading (GUI Responsiveness & Anti-Hang)**:
   * Thread antarmuka pengguna (Qt GUI Main Thread) harus bersih dari operasi I/O jaringan atau inferensi komputasi berat.
   * Setiap koneksi RTSP menggunakan mode TCP dan parameter batas waktu socket 5 detik (`stimeout=5000000`). Jika kamera dicabut/mati, thread terputus dalam 5 detik tanpa membekukan aplikasi saat ditutup.
3. **Kompatibilitas Sistem**:
   * Mendukung arsitektur Windows x86_64 (64-bit).
   * Beroperasi normal pada perangkat tanpa GPU diskrit (menggunakan akselerasi CPU SIMD/AVX2).
4. **Keamanan & Privasi**:
   * Seluruh proses analitik video berlangsung secara lokal di memori (*in-memory*).
   * Tidak ada transmisi video keluar dari jaringan privat lokal.

---

## 6. Kriteria Penerimaan (Acceptance Criteria)

| ID | Fitur | Kriteria Keberhasilan |
| :--- | :--- | :--- |
| **AC-01** | Grid Switching | Pengguna dapat berpindah dari 16, 25, dan 36 kamera dengan waktu transisi layout $\le 1.5$ detik, mematikan worker kamera yang tidak aktif. |
| **AC-02** | RTSP Sub-stream Ingestion | Aplikasi berhasil menampilkan video dari URL RTSP yang terkonfigurasi via TCP tanpa blocking melebihi 5 detik. |
| **AC-03** | Menu Decoupling | Membuka Tab 1 (Grid) memastikan model AI dalam status tidur (CPU usage rendah). Membuka Tab 2 langsung mengaktifkan AI. |
| **AC-04** | People Counter Tracking | Orang yang melintasi segmen garis virtual berhingga menambah angka MASUK/KELUAR secara instan di layar; orang yang melintas di luar batas ujung garis tidak terhitung. |
| **AC-05** | Counter Reset | Menekan tombol "Reset Counter" langsung mengembalikan nilai Masuk, Keluar, dan Di Dalam ke angka 0. |
| **AC-06** | Windows Deployment | Aplikasi dapat dijalankan di lingkungan Windows tanpa pesan error dependensi hilang dan dapat ditutup bersih tanpa hang. |
