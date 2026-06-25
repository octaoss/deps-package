# Serverless Linux Repository Manager (APT & YUM/DNF)

Repository ini berisi sistem manajemen repositori paket Linux yang **100% Serverless** untuk **Ubuntu/Debian (APT)** dan **Fedora/RHEL (DNF/YUM)**.

Dengan metode ini:
- **Metadata Indeks Repositori** dibangun secara lokal menggunakan skrip pembangun dan disajikan secara gratis melalui **Cloudflare Pages** (atau Netlify) langsung di direktori utama repositori Anda.
- **File Paket Binary (`.deb` dan `.rpm`)** tidak diunggah ke Git atau GitHub Pages, melainkan diunduh langsung dari tautan absolut luar seperti **GitHub Releases**.
- Anda memiliki kontrol penuh secara lokal untuk menambahkan atau menghapus paket kapan pun Anda inginkan menggunakan skrip Python sederhana.

---

## Cara Kerja Sistem
1. Anda menjalankan skrip `add_package.py` di komputer lokal Anda dengan memberikan parameter tautan absolut berkas paket (misalnya tautan aset di GitHub Releases).
2. Skrip secara otomatis:
   - Mengunduh berkas paket ke dalam folder *cache* lokal `packages_cache/` (folder ini otomatis diabaikan oleh Git melalui `.gitignore`).
   - Mencatat pemetaan nama berkas ke tautan unduhannya di dalam berkas `packages.json`.
   - Menggunakan perkakas standar (`apt-ftparchive` dan `createrepo_c`) untuk mengekstrak metadata dan menyusun struktur repositori APT (`debian/`) dan YUM (`fedora/`) langsung di root workspace Anda.
   - Mengubah lokasi file paket dalam indeks menjadi tautan unduhan absolut yang Anda berikan.
   - Menghasilkan berkas konfigurasi client, halaman landing page interaktif (`index.html`), serta modul penjelajah folder (*autoindex*) di setiap subdirektori untuk mencegah error 404 pada GitHub Pages.
3. Anda cukup melakukan `git commit` dan `git push` berkas metadata tersebut ke GitHub.
4. Komputer client akan mengunduh indeks dari Cloudflare Pages Anda, dan ketika memasang paket, mereka akan dialihkan (redirect 302) untuk mengunduhnya langsung dari GitHub Releases secara transparan.

---

## Persiapan Awal (Prasyarat Lokal)

Karena pembuatan metadata dilakukan di komputer lokal Anda, pastikan perkakas berikut telah terpasang di sistem Linux Anda:

```bash
# Untuk Ubuntu / Debian / Mint:
sudo apt update
sudo apt install apt-utils createrepo-c gpg

# Untuk Fedora / RHEL / CentOS:
sudo dnf install dpkg-dev createrepo_c gpg
```

---

## Cara Menambahkan Paket (.deb atau .rpm)

Jalankan skrip `add_package.py` dengan memberikan argumen URL absolut berkas paket Anda:

```bash
# Contoh menambahkan paket Debian (.deb) dari GitHub Releases
python3 add_package.py https://github.com/octaoss/deps-package/releases/download/v1.0.0/octanopilot_1.0.0_amd64.deb

# Contoh menambahkan paket Fedora (.rpm) dari GitHub Releases
python3 add_package.py https://github.com/octaoss/deps-package/releases/download/v1.0.0/octanopilot-1.0.0-1.x86_64.rpm
```

Skrip ini akan secara otomatis memperbarui direktori kerja lokal Anda. Anda dapat menambahkan banyak paket secara bergiliran dengan menjalankan kembali perintah tersebut untuk tautan paket lainnya. Semua paket yang telah ditambahkan sebelumnya akan tetap dipertahankan di dalam repositori.

---

## Cara Mempublikasikan ke Cloudflare Pages

Setelah Anda selesai menambahkan paket baru secara lokal, jalankan perintah Git standar berikut untuk mempublikasikan repositori Anda:

```bash
git add .
git commit -m "Update repository: menambahkan paket terbaru"
git push origin main
```

Hubungkan repositori Anda ke platform deployment pilihan Anda (seperti Cloudflare Pages atau Cloudflare Workers). Setiap kali Anda melakukan `git push` dan mendeploy file statis ini, situs repositori Anda akan otomatis diperbarui. Halaman panduan interaktif dan daftar paket tersedia di tautan:
**`https://deps-package.oktanio.workers.dev/`**

---

## Cara Pengguna Pakai (Client Installation)

### A. Cara Pasang di Ubuntu / Debian (APT)
Jalankan perintah berikut di terminal komputer client:

1. **Daftarkan Kunci Keamanan GPG (Jika Repositori Ditandatangani):**
   *(Jika Anda memiliki kunci GPG lokal, skrip otomatis akan menandatangani repositori dan mengekspor kunci publik Anda)*
   ```bash
   curl -fsSL https://deps-package.oktanio.workers.dev/public.key | sudo gpg --dearmor -o /etc/apt/keyrings/deps-package.gpg
   ```

2. **Tambahkan Repositori ke Daftar Sumber (Sources List):**
   * **Metode 1: Dengan Keamanan GPG (Sangat Direkomendasikan)**
     ```bash
     echo "deb [signed-by=/etc/apt/keyrings/deps-package.gpg] https://deps-package.oktanio.workers.dev/debian stable main" | sudo tee /etc/apt/sources.list.d/deps-package.list
     ```
   * **Metode 2: Tanpa GPG (Menggunakan opsi bypass tepercaya)**
     ```bash
     echo "deb [trusted=yes] https://deps-package.oktanio.workers.dev/debian stable main" | sudo tee /etc/apt/sources.list.d/deps-package.list
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
   sudo curl -sL https://deps-package.oktanio.workers.dev/fedora/deps-package.repo -o /etc/yum.repos.d/deps-package.repo
   ```

2. **Perbarui Cache dan Pasang Paket:**
   ```bash
   sudo dnf makecache
   sudo dnf install <nama-paket>
   ```
