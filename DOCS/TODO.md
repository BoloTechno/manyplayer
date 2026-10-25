# PROJECT PROGRESS & TODO TRACKER

**Proyek**: ManyPlayer - Multi-Camera RTSP Monitoring & AI People Counter  
**Pola Arsitektur**: **Lean Clean Architecture (Domain, Core, Presentation)**  
**Target Rilis**: Windows Desktop Application (.exe)  
**Status Terkini**: **Fase 1 s/d 5 Sukses Diimplementasikan & Lolos Seluruh Pengujian (100%)**  
**Terakhir Diperbarui**: 25 Oktober 2026  

---

## 📊 Ringkasan Progres Keseluruhan

| Fase | Deskripsi | Status | Progress |
| :---: | :--- | :---: | :---: |
| **0** | Spesifikasi, Kebutuhan & Clean Architecture Blueprint | **COMPLETED** | 100% |
| **1** | Setup Lingkungan Proyek & Mock RTSP | **COMPLETED** | 100% |
| **2** | Domain Layer (Pure Python Geometry & Math Engine) | **COMPLETED** | 100% |
| **3** | Core Ingestion & AI Pipeline (Adapters & Throttling) | **COMPLETED** | 100% |
| **4** | Presentation Layer (PySide6 GUI Grid & Counter View) | **COMPLETED** | 100% |
| **5** | Packaging Windows (.exe) & Verification | **COMPLETED** | 100% |

---

## 📋 Daftar Rincian Tugas (Checklist)

### Fase 0: Spesifikasi & Desain Arsitektur
- [x] Menyusun `DOCS/BRD.md` (Kebutuhan bisnis, persona, batasan & ruang lingkup)
- [x] Menyusun `DOCS/PRD.md` (Spesifikasi fungsional, UI wireframe & acceptance criteria)
- [x] Menyusun `DOCS/ARCHITECTURE.md` (Clean Architecture, multithreading, zero-latency buffer & math engine)
- [x] Menyusun `DOCS/WORKFLOW.md` & `DOCS/TODO.md` (Panduan siklus pengerjaan & pelacak otomatis)

---

### Fase 1: Setup Lingkungan Proyek & RTSP Mock Simulator
- [x] Inisialisasi struktur direktori Lean Clean Architecture (`src/domain/`, `src/core/`, `src/presentation/`, `tests/`)
- [x] Menyusun `requirements.txt` (PySide6, opencv-python, ultralytics, numpy, pytest)
- [x] Menyiapkan berkas konfigurasi default `config/cameras.json` (template 36 kamera)
- [x] Membuat skrip simulator RTSP lokal / generator video sintetis (`tests/mock_stream.py`)

---

### Fase 2: Domain Layer (Pure Python Geometry & Math Engine)
- [x] Implementasi Geometri Segmen Berhingga (`src/domain/geometry.py`):
  - [x] `Point` & `LineSegment` value objects
  - [x] Rumus `CCW` (Counter-Clockwise) dan perpotongan dua segmen berhingga
  - [x] Vektor arah (Masuk vs Keluar)
- [x] Implementasi Entitas Inti (`src/domain/entities.py`):
  - [x] `Camera`, `CounterState`, `TrackedPerson`
- [x] Implementasi Layanan Garis Lintasan (`src/domain/crossing_service.py`):
  - [x] Evaluasi perpotongan lintasan gerak kaki terhadap segmen pintu
  - [x] Mekanisme debounce ID pelacakan anti double-count
- [x] Automated Unit Testing Domain (100% Offline):
  - [x] `tests/unit/test_geometry.py` (Tes titik potong dan uji orang di luar kusen pintu lolos)
  - [x] `tests/unit/test_crossing.py` (Tes arah Masuk, Keluar, dan Debounce lolos)

---

### Fase 3: Core Ingestion & AI Pipeline (Adapters & Throttling)
- [x] Penyimpanan Konfigurasi: `src/core/camera_store.py` (Load & Save `cameras.json`)
- [x] Buffer Gambar Terpusat: `src/core/frame_store.py` (`SharedFrameStore` slot memori per kamera)
- [x] Stream Ingestion Worker: `src/core/stream_worker.py`:
  - [x] Koneksi RTSP via TCP dengan socket timeout 5 detik (`stimeout=5000000`)
  - [x] Drop-frame LIFO buffer (Zero latency)
  - [x] Auto-reconnect watchdog (5 detik)
- [x] Worker Pool Dinamis: `src/core/worker_pool.py`:
  - [x] Throttling: Hanya menghidupkan worker untuk kamera aktif (16, 25, atau 36)
  - [x] Mematikan worker kamera yang tidak terlihat untuk hemat CPU
- [x] AI Detection & Tracking:
  - [x] `src/core/ai_detector.py` (Wrapper YOLOv8n kelas person, CPU/ONNX)
  - [x] `src/core/ai_tracker.py` (Simple Euclidean centroid tracker)

---

### Fase 4: Presentation Layer (PySide6 Native Windows GUI)
- [x] Tampilan Grid Monitor (Menu 1):
  - [x] `src/presentation/widgets/video_tile.py` (Sel video proporsional 16:9 + label nama)
  - [x] `src/presentation/grid_view.py` (Layout 4x4 [16], 5x5 [25], 6x6 [36] kamera)
  - [x] **Master UI Render Timer (15 FPS)**: Menarik frame terlihat secara berkala (Pull-based) tanpa membekukan antarmuka
- [x] Tampilan AI People Counter (Menu 2):
  - [x] `src/presentation/widgets/hud_overlay.py` (Panel semi-transparan angka Masuk, Keluar, Di Dalam & garis lintasan)
  - [x] `src/presentation/counter_view.py` (Mode 1 Kamera Fokus / 2 Kamera Split + Tombol Reset)
- [x] Dialog GUI Kelola Kamera (CRUD RTSP Modal):
  - [x] `src/presentation/dialogs/camera_config_dialog.py` (Tabel interaktif: Tambah, Hapus, Uji Koneksi RTSP non-blocking, Simpan & Terapkan)
  - [x] Tombol navigasi `[ ⚙️ KELOLA KAMERA ]` di navbar `src/presentation/main_window.py`
  - [x] Live reload konfigurasi seketika tanpa me-restart aplikasi
- [x] Jendela Utama & Decoupling:
  - [x] `src/presentation/main_window.py` (Shell navigasi Tab Menu 1 & Menu 2)
  - [x] **State Decoupling**: AI otomatis dimatikan saat membuka Menu 1
- [x] Composition Root: `src/main.py` (Entry point aplikasi + dukungan `--mock` simulation mode)

---

### Fase 5: Integrasi, Packaging Windows (.exe) & UAT
- [x] Menyusun spesifikasi bundler PyInstaller `build_windows.spec`
- [x] Pengujian performa & runtime (`tests/unit/test_gui_headless.py` & mock verification)
- [x] Pembuatan berkas petunjuk penggunaan bagi operator (`README.md`)

---

## 📝 Log Pembaruan Progres

| Tanggal | Fase Terkait | Catatan Pembaruan | Diperbarui Oleh |
| :--- | :---: | :--- | :--- |
| 25-10-2026 | Fase 0 | Dokumen BRD, PRD, ARCHITECTURE, WORKFLOW, dan TODO selesai dibuat. | Antigravity AI |
| 25-10-2026 | Fase 0 | Arsitektur ditingkatkan ke standar **Clean Architecture**. | Antigravity AI |
| 25-10-2026 | Fase 0 | Hardening arsitektur v2.1: finite segment crossing, pull-based 15 FPS master timer, dynamic worker throttling, RTSP socket timeout 5s, dan lean structure (-180 baris boilerplate). | Antigravity AI |
| 25-10-2026 | Fase 1 - 5 | Seluruh kode diimplementasikan (Domain, Core, Presentation, GUI, Mock generator, Build spec, README) dan 12 unit tests 100% PASSED. | Antigravity AI |
| 25-10-2026 | Code Hardening | 5 Temuan review diperbaiki: AnalyticsWorker di background thread (anti-freeze UI), HUD scaling 16:9, continuous RTSP read (zero latency), frame sequence caching (hemat CPU/RAM), dan module-level imports. | Antigravity AI |
| 25-10-2026 | Audit Fixes | 6 Temuan audit diperbaiki: Tripwire normalisasi dinamis (1080p/4K ready), isolasi instance YOLO & mutex lock, safe single-thread OpenCV release, bounded O(1) trajectory memory (anti-leak 24/7), robust worker joining, dan 80x45 small-screen scaling. Seluruh 15 unit tests 100% PASSED. | Antigravity AI |
| 25-10-2026 | Fitur GUI Kelola Kamera | Implementasi Dialog GUI Kelola Kamera (CRUD RTSP URLs, uji koneksi non-blocking, live reload tanpa restart), tombol navbar [ ⚙️ KELOLA KAMERA ], dan 6 unit test baru. Seluruh 21 unit tests 100% PASSED. | Antigravity AI |
| 25-10-2026 | Review Fixes | 6 Temuan review kode diperbaiki: deteksi pergantian URL RTSP di WorkerPool, penugasan Cam 1/Cam 2 presisi, proteksi FFmpeg max_delay, pembersihan thread tes koneksi pada reject/close, auto-reset headcount saat kamera counter ditukar, dan pencegahan worker thrashing pada GridView. Seluruh 23 unit tests 100% PASSED. | Antigravity AI |
| 25-10-2026 | Audit Fixes (Repo-Wide) | 8 Temuan audit diperbaiki: Dukungan custom non-contiguous ID kamera pada GridView, penyimpanan atomik & pemulihan korupsi pada CameraStore, build_windows.spec siap offline (bundel weights YOLO & hiddenimports), .gitignore komprehensif, unit test AnalyticsWorker, eliminasi monkey-patching via Qt signal, uji koneksi kolom Main-Stream, dan pembersihan parameter mati. Seluruh 25 unit tests 100% PASSED. | Antigravity AI |
