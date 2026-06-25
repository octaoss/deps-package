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

## Cara Penggunaan & Rilis Paket

Untuk menambahkan paket baru ke dalam repositori Anda, Anda hanya perlu membuat sebuah rilis baru di GitHub:

1. Masuk ke halaman repositori Anda, lalu klik **Releases** > **Create a new release** (atau rancang draf rilis baru).
2. Buat tag baru (misalnya `v1.0.0`) dan isi informasi rilis.
3. Di bagian **Attach binaries...**, unggah file `.deb` dan/atau `.rpm` hasil build Anda.
4. Klik **Publish release**.
5. GitHub Actions akan otomatis berjalan (`Update Linux Package Repository`) untuk membangun ulang metadata repositori dan memperbarui halaman GitHub Pages Anda dalam hitungan detik.

---

## Cara Pengguna Pakai (Client Installation)

Setelah repositori Anda aktif di GitHub Pages (misalnya pada tautan `https://username.github.io/repo-name`), pengguna/client Anda dapat mendaftarkan repositori tersebut ke sistem mereka dan langsung memasang paket Anda dengan sangat mudah.

> [!NOTE]
> Ganti `username` dan `repo-name` pada perintah di bawah ini sesuai dengan nama akun GitHub dan nama repositori Anda.

### A. Cara Pasang di Ubuntu / Debian (APT)
Jalankan perintah berikut di terminal komputer client:

1. **Daftarkan Kunci Keamanan GPG (Jika Repositori Ditandatangani):**
   ```bash
   curl -fsSL https://username.github.io/repo-name/public.key | sudo gpg --dearmor -o /etc/apt/keyrings/deps-package.gpg
   ```

2. **Tambahkan Repositori ke Daftar Sumber (Sources List):**
   * **Metode 1: Dengan Keamanan GPG (Sangat Direkomendasikan)**
     ```bash
     echo "deb [signed-by=/etc/apt/keyrings/deps-package.gpg] https://username.github.io/repo-name/debian stable main" | sudo tee /etc/apt/sources.list.d/deps-package.list
     ```
   * **Metode 2: Tanpa GPG (Menggunakan opsi bypass tepercaya)**
     ```bash
     echo "deb [trusted=yes] https://username.github.io/repo-name/debian stable main" | sudo tee /etc/apt/sources.list.d/deps-package.list
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
   sudo curl -sL https://username.github.io/repo-name/fedora/deps-package.repo -o /etc/yum.repos.d/deps-package.repo
   ```

2. **Perbarui Cache dan Pasang Paket:**
   ```bash
   sudo dnf makecache
   sudo dnf install <nama-paket>
   ```

