---
name: git-commit-id
description: >-
  Membuat pesan git commit profesional dalam Bahasa Indonesia mengikuti standar Conventional Commits,
  memeriksa git status dan git diff, memverifikasi tidak ada kredensial atau file binary sementara,
  dan mengeksekusi commit/push ke GitHub. Gunakan skill ini saat pengguna meminta commit dalam bahasa Indonesia,
  "buat commit", "commit perubahan", "commit ke github", "git commit", atau /git-commit-id.
---

# Git Commit Bahasa Indonesia (git-commit-id)

Skill ini memandu pembuatan pesan git commit yang terstruktur, rapi, dan mudah dibaca dalam **Bahasa Indonesia** dengan standar industri **Conventional Commits**.

---

## 1. Prosedur Kerja

### Langkah 1: Pemeriksaan Status & Diff
Sebelum membuat pesan commit:
1. Jalankan `git status --short` untuk melihat file yang dimodifikasi, ditambah, atau dihapus.
2. Jalankan `git diff` (atau `git diff --cached`) untuk meninjau perubahan kode secara mendalam.
3. **Pemeriksaan Keamanan & Kebersihan**:
   - Pastikan tidak ada file rahasia/kredensial yang terikut (misal: password, token, API key, `cameras.json`).
   - Pastikan tidak ada file binary cache atau temporer yang masuk (misal: `__pycache__`, `*.pyc`, `*.tmp`).

---

### Langkah 2: Penyusunan Pesan Commit (Conventional Commits)

Gunakan struktur standar berikut:
```text
<tipe>(<cakupan>): <judul ringkas dalam bahasa Indonesia>

[Deskripsi mendalam / poin-poin perubahan jika mencakup lebih dari satu hal]
```

#### Aturan Format:
- **Tipe Commit**:
  - `feat`: Fitur atau fungsionalitas baru untuk pengguna.
  - `fix`: Perbaikan bug atau kegagalan sistem.
  - `security`: Pengamanan kredensial, proteksi rahasia, atau mitigasi celah keamanan.
  - `refactor`: Penyederhanaan atau restrukturisasi kode tanpa mengubah fungsionalitas.
  - `perf`: Optimasi performa, pengurangan latensi, atau penghematan CPU/memori.
  - `docs`: Pembaruan dokumentasi, README, panduan, atau walkthrough.
  - `test`: Penambahan atau perbaikan unit test dan integration test.
  - `chore`: Perubahan konfigurasi alat, `.gitignore`, build script, atau dependensi.
- **Cakupan (`scope`)**: Komponen atau modul yang dipengaruhi (contoh: `grid`, `stream`, `worker`, `config`, `auth`).
- **Judul**:
  - Ditulis dalam Bahasa Indonesia yang lugas dan ringkas (maksimal 72 karakter).
  - Menggunakan bentuk kalimat aktif/imperatif (contoh: *"tambahkan kontrol stream"*, bukan *"menambahkan"* atau *"menambahkanlah"*).
  - Tetap pertahankan istilah teknis baku dalam bahasa aslinya (contoh: *cache*, *thread*, *socket*, *stream*, *demuxer*, *timeout*).
- **Body (Poin Penjelasan)**:
  - Berikan rincian jika ada beberapa komponen penting yang diperbaiki.
  - Jelaskan *mengapa* perubahan tersebut dibuat jika konteksnya tidak tampak langsung dari kodenya.

---

### Langkah 3: Konfirmasi dan Eksekusi
1. Tampilkan draf pesan commit dan daftar file yang terpengaruh kepada pengguna.
2. Setelah disetujui pengguna (atau jika pengguna meminta langsung eksekusi), jalankan:
   ```bash
   git add <file-file-relevan>
   git commit -m "<pesan commit>"
   ```
3. Tampilkan hasil commit dengan `git log -1 --stat` untuk memberikan visibilitas penuh.
