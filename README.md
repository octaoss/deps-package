# Serverless Linux Repository Manager (APT & YUM/DNF)

Repository ini berisi sistem otomatisasi penuh untuk membuat dan mengelola repositori paket Linux Anda sendiri, baik untuk **Ubuntu/Debian (APT)** maupun **Fedora/RHEL (DNF/YUM)**. 

Berbeda dengan metode tradisional yang membutuhkan server web aktif (VPS) untuk meng-host file `.deb` atau `.rpm` berukuran besar, sistem ini **100% Serverless**:
- **Metadata Indeks (Repository Indexes)** disimpan dan disajikan secara gratis melalui **GitHub Pages**.
- **File Paket Binary (`.deb` dan `.rpm`)** disimpan dan diunduh langsung dari **GitHub Releases**.
- **Otomatisasi Penuh** menggunakan **GitHub Actions** yang akan berjalan secara otomatis setiap kali Anda merilis versi baru di GitHub.

---

## Cara Kerja
1. Anda mempublikasikan sebuah **GitHub Release** dan melampirkan file `.deb` dan/atau `.rpm` sebagai aset rilis.
2. **GitHub Actions** mendeteksi rilis baru, lalu secara otomatis:
   - Mengunduh seluruh file `.deb` dan `.rpm` dari semua rilis sebelumnya.
   - Mengekstrak metadata paket untuk membuat berkas indeks repositori (`Packages`, `Release`, dan metadata YUM).
   - Mengubah lokasi file (path) dalam metadata menjadi **URL Absolut** yang mengarah langsung ke GitHub Releases.
   - Menandatangani repositori menggunakan kunci GPG Anda (jika dikonfigurasi).
   - Menghasilkan file konfigurasi client (`.repo`) dan halaman dokumentasi (`index.html`) yang sangat informatif.
   - Menyebarkan (deploy) seluruh metadata tersebut ke branch `gh-pages` untuk disajikan oleh GitHub Pages.
3. Komputer client dapat memasang paket Anda menggunakan `apt install` atau `dnf install` standar. Saat mengunduh, package manager client akan mengunduh langsung dari CDN GitHub Releases.

---

## Struktur File Repository
Setelah sistem disebarkan ke GitHub Pages, struktur berkas di branch `gh-pages` akan seperti berikut:
```text
gh-pages/
├── index.html                # Halaman panduan instalasi & daftar paket (dibuat otomatis)
├── public.key                # Public key GPG untuk verifikasi client (jika GPG dikonfigurasi)
├── debian/                   # APT Repository Root
│   ├── public.key
│   └── dists/
│       └── stable/
│           └── main/
│               ├── binary-amd64/
│               │   ├── Packages      # Indeks paket dengan URL absolut ke GitHub Releases
│               │   └── Packages.gz
│               ├── Release           # Metadata rilis APT
│               ├── Release.gpg       # Tanda tangan terpisah (GPG)
│               └── InRelease         # Tanda tangan tertanam (GPG)
└── fedora/                   # YUM/DNF Repository Root
    ├── public.key
    ├── deps-oktanio.repo     # Berkas konfigurasi YUM client (dibuat otomatis)
    ├── deps-package.repo     # Berkas konfigurasi YUM client alternatif
    └── repodata/             # Metadata YUM/DNF dengan URL absolut ke GitHub Releases
```

---

## Langkah-Langkah Setup awal

### 1. Aktifkan GitHub Pages di Repository Anda
1. Masuk ke halaman repositori Anda di GitHub.
2. Buka menu **Settings** > **Pages**.
3. Di bagian **Build and deployment**:
   - Source: Pilih **Deploy from a branch**.
   - Branch: Pilih **gh-pages** dan folder **/(root)**, lalu klik **Save**.
   *(Catatan: Branch `gh-pages` akan dibuat secara otomatis oleh GitHub Actions pada rilis pertama Anda).*

### 2. Konfigurasi Kunci Keamanan GPG (Sangat Direkomendasikan)
Secara default, jika Anda tidak mengonfigurasi GPG, repositori akan dibuat tanpa tanda tangan (unsigned), yang mengharuskan client menggunakan opsi `[trusted=yes]`. Untuk keamanan produksi, sangat disarankan menandatangani repositori menggunakan GPG:

1. Buat kunci GPG baru di komputer lokal Anda jika belum punya:
   ```bash
   gpg --generate-key
   ```
2. Ekspor private key Anda dalam format teks (ASCII armored):
   ```bash
   gpg --export-secret-keys --armor "Nama Kunci GPG Anda"
   ```
3. Salin seluruh teks output (termasuk baris `-----BEGIN PGP PRIVATE KEY-----` dan `-----END PGP PRIVATE KEY-----`).
4. Di halaman repositori GitHub Anda, buka **Settings** > **Secrets and variables** > **Actions**.
5. Klik **New repository secret**, beri nama **`GPG_PRIVATE_KEY`**, tempel teks private key tersebut, dan klik **Add secret**.

---

## Cara Menambahkan Paket (.deb & .rpm)

Sistem ini dirancang sangat fleksibel. Anda tidak perlu mengunggah file binary secara manual ke server web atau melakukan konfigurasi command-line yang rumit. Cukup unggah berkas `.deb` dan `.rpm` Anda ke **GitHub Releases**, dan sistem akan melakukan sisanya secara otomatis.

Terdapat dua cara untuk menambahkan dan mengunggah berkas paket Anda:

### Metode 1: Secara Manual (Melalui Antarmuka Web GitHub)

Ini adalah cara termudah jika Anda melakukan kompilasi/build paket secara lokal di komputer Anda:

1. **Siapkan File Paket Anda:** Pastikan Anda telah mem-build berkas `.deb` (untuk Debian/Ubuntu) atau `.rpm` (untuk Fedora/CentOS) di komputer lokal Anda.
2. **Buka Halaman Rilis:** Masuk ke repositori Anda di GitHub, lalu klik menu **Releases** di kolom sebelah kanan, kemudian klik tombol **Draft a new release** (atau **Create a new release**).
3. **Tentukan Tag & Judul Rilis:**
   - Buat tag baru, misalnya `v1.0.0` (disarankan menggunakan format semantic versioning).
   - Berikan judul rilis, misalnya `Release v1.0.0`.
4. **Unggah Berkas Paket Anda:**
   - Tarik (drag and drop) atau klik area **Attach binaries by dropping them here or selecting them** di bagian bawah editor rilis.
   - Pilih berkas `.deb` dan `.rpm` yang ingin Anda masukkan ke dalam repositori.
5. **Publikasikan Rilis:** Klik tombol **Publish release** yang berwarna hijau di bagian bawah.
6. **Tunggu Otomatisasi Selesai:** Setelah dipublikasikan, GitHub Actions (`Update Linux Package Repository`) akan mendeteksi rilis baru ini secara otomatis. Tindakan ini akan mengunduh paket tersebut, mengekstrak metadatanya, membangun indeks repositori, dan memperbarui situs web GitHub Pages Anda dalam beberapa detik.

---

### Metode 2: Secara Otomatis (Melalui Pipeline CI/CD / GitHub Actions)

Jika Anda ingin membangun berkas `.deb` dan `.rpm` secara otomatis dari kode sumber Anda dan langsung merilisnya ke repositori paket ini, Anda dapat menggunakan perintah `gh` CLI dalam alur kerja GitHub Actions Anda.

Berikut adalah contoh potongan baris alur kerja (workflow) untuk mempublikasikan rilis beserta asetnya secara otomatis:

```yaml
      - name: Build Packages
        run: |
          # Perintah kompilasi/build aplikasi Anda di sini
          # Misalnya menghasilkan: build/myapp_1.0.0_amd64.deb dan build/myapp-1.0.0-1.x86_64.rpm

      - name: Create GitHub Release & Upload Assets
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh release create v1.0.0 build/*.deb build/*.rpm \
            --title "Release v1.0.0" \
            --notes "Rilis otomatis dari alur kerja CI/CD."
```

Setiap kali alur kerja rilis otomatis di atas dijalankan, sistem repositori paket Anda akan langsung mendeteksinya dan memperbarui indeks paket di GitHub Pages secara real-time.

---

### Ketentuan Penting & Tips Keamanan

- **Informasi Paket Otomatis:** Anda tidak perlu menulis versi atau deskripsi paket secara manual di repositori ini. Skrip otomatisasi akan membaca langsung file control/spec yang ada di dalam berkas `.deb` dan `.rpm` Anda untuk mendapatkan informasi Nama Paket, Versi, Arsitektur, dan Deskripsi untuk ditampilkan di landing page.
- **Mendukung Banyak Paket & Versi:** Anda dapat mengunggah beberapa berkas `.deb` dan `.rpm` yang berbeda ke dalam satu rilis tunggal, atau membaginya ke dalam beberapa rilis berbeda. Sistem otomatisasi akan memindai **seluruh rilis** yang ada di repositori Anda dan menggabungkannya ke dalam satu indeks repositori tunggal yang utuh.
- **Penghapusan Paket:** Jika Anda ingin menghapus suatu paket dari repositori, Anda cukup menghapus file aset dari rilis tersebut atau menghapus rilis itu sepenuhnya dari halaman GitHub. Alur kerja akan secara otomatis membangun kembali indeks repositori Anda tanpa paket yang telah dihapus pada jalannya alur kerja berikutnya.

---

## Cara Pengguna Pakai (Client Installation)

Setelah repositori Anda aktif di GitHub Pages pada tautan `https://octaoss.github.io/deps-package/`, pengguna/client Anda dapat mendaftarkan repositori tersebut ke sistem mereka dan langsung memasang paket Anda dengan sangat mudah.

### A. Cara Pasang di Ubuntu / Debian (APT)
Jalankan perintah berikut di terminal komputer client:

1. **Daftarkan Kunci Keamanan GPG (Jika Repositori Ditandatangani):**
   ```bash
   curl -fsSL https://octaoss.github.io/deps-package/public.key | sudo gpg --dearmor -o /etc/apt/keyrings/deps-package.gpg
   ```

2. **Tambahkan Repositori ke Daftar Sumber (Sources List):**
   * **Metode 1: Dengan Keamanan GPG (Sangat Direkomendasikan)**
     ```bash
     echo "deb [signed-by=/etc/apt/keyrings/deps-package.gpg] https://octaoss.github.io/deps-package/debian stable main" | sudo tee /etc/apt/sources.list.d/deps-package.list
     ```
   * **Metode 2: Tanpa GPG (Menggunakan opsi bypass tepercaya)**
     ```bash
     echo "deb [trusted=yes] https://octaoss.github.io/deps-package/debian stable main" | sudo tee /etc/apt/sources.list.d/deps-package.list
     ```

3. **Perbarui Cache dan Pasang Paket:**
   ```bash
   sudo apt update
   sudo apt install <nama-paket>
   ```

---

### B. Cara Pasang di Fedora / RHEL / CentOS (DNF/YUM)
Jalankan perintah berikut di terminal komputer client:

1. **Unduh File Konfigurasi Repositori secara Otomatis:**
   ```bash
   sudo curl -sL https://octaoss.github.io/deps-package/fedora/deps-package.repo -o /etc/yum.repos.d/deps-package.repo
   ```

2. **Perbarui Cache dan Pasang Paket:**
   ```bash
   sudo dnf makecache
   sudo dnf install <nama-paket>
   ```

