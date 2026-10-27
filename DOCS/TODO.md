# PROJECT PROGRESS & TODO TRACKER

**Proyek**: ManyPlayer - Dedicated Ultra-Lightweight RTSP Multi-Camera Surveillance Wall  
**Pola Arsitektur**: **Lean Clean Architecture (Domain, Core, Presentation)**  
**Target Rilis**: Windows Desktop Application (.exe)  
**Status Terkini**: **Streamlining Selesai (Pure RTSP Surveillance Viewer) & 100% Unit Tests Passed**  
**Terakhir Diperbarui**: 27 Oktober 2026  

---

## 📊 Ringkasan Progres Keseluruhan

| Fase | Deskripsi | Status | Progress |
| :---: | :--- | :---: | :---: |
| **0** | Spesifikasi, Kebutuhan & Clean Architecture Blueprint | **COMPLETED** | 100% |
| **1** | Setup Lingkungan Proyek & Mock RTSP Simulator | **COMPLETED** | 100% |
| **2** | Domain Layer (Camera Entity & Storage Rules) | **COMPLETED** | 100% |
| **3** | Core Ingestion Pipeline (Adapters, Throttling & Deduplication) | **COMPLETED** | 100% |
| **4** | Presentation Layer (Unified Header PySide6 Grid Video Wall) | **COMPLETED** | 100% |
| **5** | Packaging Windows (.exe) & Verification | **COMPLETED** | 100% |

---

## 📋 Daftar Rincian Tugas (Checklist)

### Fase 0: Spesifikasi & Desain Arsitektur
- [x] Menyusun `DOCS/BRD.md` (Kebutuhan bisnis, persona, batasan & ruang lingkup)
- [x] Menyusun `DOCS/PRD.md` (Spesifikasi fungsional, UI wireframe & acceptance criteria)
- [x] Menyusun `DOCS/ARCHITECTURE.md` (Clean Architecture, multithreading, zero-latency buffer)
- [x] Menyusun `DOCS/WORKFLOW.md` & `DOCS/TODO.md` (Panduan siklus pengerjaan & pelacak otomatis)

---

### Fase 1: Setup Lingkungan Proyek & RTSP Mock Simulator
- [x] Inisialisasi struktur direktori Lean Clean Architecture (`src/domain/`, `src/core/`, `src/presentation/`, `tests/`)
- [x] Perampingan dependensi `requirements.txt` (Hanya PySide6, opencv-python, numpy, pytest — bebas dependensi berat PyTorch & Ultralytics)
- [x] Penyeragaman berkas konfigurasi default `config/cameras.json` & `config/cameras.example.json` (36 kamera dengan 1 `stream_url` per kamera)
- [x] Simulator RTSP lokal / generator video sintetis (`tests/mock_stream.py`)

---

### Fase 2: Domain Layer (Pure Python Entities)
- [x] Entitas inti `src/domain/entities.py`:
  - [x] `Camera` (id, name, stream_url) dengan backward-compatible alias untuk `sub_stream_url` & `main_stream_url`
- [x] Penghapusan tuntas entitas dan service AI yang usang:
  - [x] Eliminasi `TrackedPerson`, `CounterState`, `domain/crossing_service.py`, `domain/geometry.py`

---

### Fase 3: Core Video Ingestion & Stream Management
- [x] Penyimpanan Konfigurasi: `src/core/camera_store.py`:
  - [x] Load & Save `cameras.json` dengan dukungan format tunggal `stream_url` dan fallback parsing
  - [x] Penyimpanan atomik dengan safe file replacement
- [x] Buffer Gambar Terpusat: `src/core/frame_store.py` (`SharedFrameStore` slot memori per kamera)
- [x] Stream Ingestion Worker: `src/core/stream_worker.py`:
  - [x] Koneksi RTSP via TCP dengan socket timeout 3-5 detik
  - [x] Drop-frame LIFO buffer (Zero latency)
  - [x] Auto-reconnect watchdog & graceful socket cleanup
- [x] In-Process RTSP Bridge: `src/core/rtsp_bridge.py` untuk sanitasi otentikasi RTSP Hikvision
- [x] Worker Pool Dinamis: `src/core/worker_pool.py`:
  - [x] Throttling cerdas: Hanya menghidupkan worker untuk kamera terlihat (16, 25, atau 36)
  - [x] Deduplikasi RTSP & Fan-out cerdas (1 koneksi fisik untuk URL bersama)
  - [x] Dead worker zombie eviction & automatic recovery

---

### Fase 4: Presentation Layer (Unified PySide6 Grid Video Wall)
- [x] Tampilan Grid Video Wall:
  - [x] `src/presentation/widgets/video_tile.py` (Sel video proporsional, OSD smart margin placement, border highlight seleksi)
  - [x] `src/presentation/grid_view.py` (Layout 4x4 [16], 5x5 [25], 6x6 [36] kamera)
  - [x] Master UI Render Timer (15 FPS pull-based, anti-freeze)
  - [x] Drag & Drop Slot Swapping (Penukaran posisi kamera instan tanpa putus koneksi)
  - [x] Preservasi Aspek Rasio (Auto / 16:9 / 4:3 / Penuh) & Mode OSD (Smart / Hover / Sembunyi)
  - [x] Mode Fokus (1x1) & Mode Layar Penuh (Fullscreen F11 / Esc bertingkat)
- [x] Header Terpadu Satu Baris (*Unified Top Header*):
  - [x] Penggabungan logo branding `📹 MANYPLAYER`, status live, kontrol stream, layout switcher, rasio, OSD, tombol `[ ⚙️ Kelola Kamera ]`, dan `[ ⛶ Fullscreen ]` ke dalam satu toolbar di `GridView`
  - [x] Penghapusan tab navbar terpisah dan widget stack multi-halaman
- [x] Dialog Kelola Kamera Ringkas (`src/presentation/dialogs/camera_config_dialog.py`):
  - [x] Tabel 3 kolom bersih: `ID Slot`, `Nama Kamera / Lokasi`, `Alamat RTSP Stream URL`
  - [x] Modal hasil uji koneksi dengan live snapshot preview 16:9 dan kartu diagnostik
  - [x] Fitur duplikasi baris (*clone row*), pencarian cepat (*live search*), dan live reload tanpa restart
- [x] Jendela Utama Bersih: `src/presentation/main_window.py` langsung memuat `GridView` sebagai central widget

---

### Fase 5: Packaging Windows (.exe) & Verifikasi
- [x] Pembaruan `build_windows.spec`:
  - [x] Menghapus exclusions & hiddenimports `torch`, `ultralytics`, dan file `yolov8n.pt`
  - [x] Estimasi ukuran binary terpangkas drastis dari ~800MB menjadi ~30MB
- [x] Verifikasi Unit Test: Seluruh 62 unit tests 100% PASSED
- [x] Verifikasi Peluncuran Aplikasi: Uji mode simulasi `--mock` berjalan sempurna tanpa error

---

## 📝 Log Pembaruan Progres

- **27 Oktober 2026 (Sore)**:
  - **Penyelesaian Ponytail Quality Audit**:
    - **Perbaikan Bug Kritis**:
      1. Menghilangkan double-close `RTSPStreamBridge` pada shutdown `StreamWorker` via atomic reference swap dan idempotent `close()`.
      2. Mencegah overflow oktet IP address pada `add_camera_row()` ketika ID > 155 (clamping host octet <= 254).
      3. Menghilangkan mutasi global `os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"]` pada `ConnectionTesterThread` dengan mengoper timeout langsung ke parameter `cv2.VideoCapture`.
    - **Pembersihan Kode Mati & Dead Fields**:
      1. Menghapus field `sub_stream_url`, `main_stream_url`, `is_counter_target`, dan `__post_init__` pada dataclass `Camera`.
      2. Menghapus parameter `is_main_stream` / `is_main` di seluruh codebase (`worker_pool`, `grid_view`, `entities`).
      3. Menghapus method mati `VideoTile.set_frame()` dan `GridView.resume_rendering()`.
      4. Menghapus unused imports `QComboBox` dan `Tuple` pada dialog konfigurasi kamera.
    - **Peningkatan Ketahanan Jaringan**:
      1. Menambahkan buffering header RTSP pada `RTSPStreamBridge._forward` sehingga respon terfragmentasi antar-paket TCP tetap tersanitasi sempurna.
    - **Pengujian Lengkap**: Menambahkan unit test baru untuk idempotent bridge close, fragmented TCP header buffering, environ preservation, dan IP octet clamp. Seluruh 62 unit test PASSED 100%.
    - **Pembersihan Dependensi Berat**: Menghapus `torch` dan `ultralytics` dari `requirements.txt` dan `build_windows.spec`, menghemat memori, siklus CPU, dan memangkas ukuran build aplikasi dari ~800MB ke ~30MB.
    - **Penyederhanaan Konfigurasi Kamera**: Seluruh 36 kamera kini menggunakan 1 URL RTSP tunggal (`stream_url`), menghilangkan kerumitan pembagian sub-stream dan main-stream.
    - **Header Terpadu Satu Baris (Unified Top Header)**: Mengintegrasikan branding aplikasi `📹 MANYPLAYER`, status feed, kontrol Play/Stop, layout (4x4, 5x5, 6x6), aspek rasio, OSD label, tombol `[ ⚙️ Kelola Kamera ]`, dan tombol `[ ⛶ Fullscreen ]` ke dalam satu baris toolbar ringkas dan elegan langsung pada Grid Monitor.
    - **Eliminasi Navbar & Tab Switching**: Menghapus tombol navigasi tab dan `QStackedWidget` di `MainWindow`, menjadikan antarmuka 100% fokus untuk pemantauan kamera CCTV.
    - **Penyederhanaan Dialog Kelola Kamera**: Tabel kamera dirampingkan menjadi 3 kolom esensial: `ID Slot`, `Nama Kamera / Lokasi`, dan `Alamat RTSP Stream URL`.
    - **Penghapusan File Usang**: Menghapus 12 berkas AI dan matematika yang tidak lagi digunakan (`ai_detector.py`, `ai_tracker.py`, `analytics_worker.py`, `crossing_service.py`, `geometry.py`, `counter_view.py`, `hud_overlay.py`, serta seluruh unit test terkait).
    - **Verifikasi Kualitas**: Seluruh 58 unit tests lolos 100% tanpa error, dan peluncuran aplikasi dengan `--mock` terverifikasi responsif dan lancar.

- **27 Oktober 2026 (Sebelumnya)**:
  - **Perbaikan Menyeluruh Berdasarkan Quality Audit (Ponytail Audit)**:
    - Dead worker zombie eviction & recovery di WorkerPool.
    - Pencegahan kebocoran socket & capture di StreamWorker via deterministik `try...finally`.
    - Resolusi path konfigurasi PyInstaller Windows (`sys.frozen`).
    - Clean shutdown Windows dengan bounded thread join di WorkerPool.
    - RTSP bridge non-blocking accept loop via thread terisolasi.
    - Optimasi CPU rendering via selektif SmoothPixmapTransform.
