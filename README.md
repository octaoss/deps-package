# Custom Linux Repository Manager

Repositori ini berisi skrip otomatisasi untuk membuat, mengelola, dan menambahkan paket (packages) ke dalam repositori linux Anda sendiri, baik untuk **Ubuntu/Debian (APT)** maupun **Fedora (DNF/YUM)**.

Secara default, repositori diarahkan ke direktori lokal `/var/www/repo/`, yang sangat ideal untuk disajikan menggunakan web server seperti Nginx atau Apache.

---

## Daftar Isi
1. [Struktur Direktori Repositori](#struktur-direktori-repositori)
2. [Setup & Penggunaan Ubuntu/Debian Repository](#1-setup--penggunaan-ubuntudebian-repository)
3. [Setup & Penggunaan Fedora Repository](#2-setup--penggunaan-fedora-repository)
4. [Konfigurasi Web Server (Nginx)](#3-konfigurasi-web-server-nginx)
5. [Konfigurasi di Sisi Client (Pengguna Repositori)](#4-konfigurasi-di-sisi-client-pengguna-repositori)
6. [Keamanan & Tanda Tangan GPG (Opsional namun Direkomendasikan)](#5-keamanan--tanda-tangan-gpg-opsional-namun-direkomendasikan)

---

## Struktur Direktori Repositori
Setelah semua setup dijalankan, struktur direktori `/var/www/repo/` akan tampak seperti berikut:
```text
/var/www/repo/
├── debian/                   # Ubuntu/Debian Repository Root
│   ├── conf/
│   │   └── release.conf      # Konfigurasi metadata APT
│   ├── pool/
│   │   └── main/             # File .deb disimpan di sini
│   └── dists/
│       └── stable/
│           └── main/
│               └── binary-amd64/
│                   ├── Packages     # Indeks paket
│                   └── Packages.gz  # Indeks terkompresi
└── fedora/                   # Fedora Repository Root
    ├── *.rpm                 # File .rpm disimpan di sini
    ├── deps-oktanio.repo     # Berkas konfigurasi client (dibuat otomatis)
    └── repodata/             # Metadata YUM/DNF (dibuat otomatis oleh createrepo)
```

---

## 1. Setup & Penggunaan Ubuntu/Debian Repository

### A. Setup Awal
Jalankan skrip `setup-ubuntu.sh` untuk menginstal dependensi (jika diperlukan), membuat struktur direktori awal, dan file konfigurasi repositori:
```bash
sudo ./setup-ubuntu.sh
```
*Catatan: Anda bisa mengubah lokasi default repositori dengan memberikan argumen, misalnya: `sudo ./setup-ubuntu.sh /jalur/ke/repo/debian`.*
*Variabel domain diatur menggunakan `REPO_URL="https://deps.oktanio.dev"` di bagian atas skrip.*

### B. Menambahkan Paket ke Ubuntu
Untuk mengunduh dan menambahkan paket `.deb` dari URL langsung ke repositori Anda, gunakan skrip `add-package-ubuntu.sh`:
```bash
sudo ./add-package-ubuntu.sh <URL_KE_FILE_DEB>
```
**Contoh:**
```bash
sudo ./add-package-ubuntu.sh https://releases.hashicorp.com/vagrant/2.4.1/vagrant_2.4.1-1_amd64.deb
```
Skrip ini secara otomatis akan:
1. Mengunduh file `.deb` menggunakan `wget` ke direktori `pool/main/`.
2. Melakukan registrasi indeks paket menggunakan `apt-ftparchive`.
3. Memperbarui berkas `Packages` dan `Release`.

---

## 2. Setup & Penggunaan Fedora Repository

### Prasyarat
Untuk mengelola repositori Fedora, Anda memerlukan tool `createrepo_c` (atau `createrepo`). Jika belum terpasang, skrip setup akan menginstalnya secara otomatis menggunakan package manager sistem Anda.

### A. Setup Awal
Jalankan skrip `setup-fedora.sh` untuk menginstal dependensi, membuat struktur direktori Fedora, menginisialisasi metadata repositori, serta membuat file konfigurasi client secara otomatis:
```bash
sudo ./setup-fedora.sh
```
*Catatan: Anda bisa mengubah lokasi default repositori dengan memberikan argumen, misalnya: `sudo ./setup-fedora.sh /jalur/ke/repo/fedora`.*
*Variabel domain diatur menggunakan `REPO_URL="https://deps.oktanio.dev"` di bagian atas skrip.*

### B. Menambahkan Paket ke Fedora (Cara Tambah Package)
Untuk menambahkan paket `.rpm` (baik dari internet berupa URL, maupun file lokal yang sudah diunduh), gunakan skrip `add-package-fedora.sh`:
```bash
sudo ./add-package-fedora.sh <URL_RPM_ATAU_JALUR_FILE_LOKAL>
```
**Contoh 1 (Menggunakan URL):**
```bash
sudo ./add-package-fedora.sh https://nginx.org/packages/mainline/centos/9/x86_64/RPMS/nginx-1.25.3-1.el9.ngx.x86_64.rpm
```
**Contoh 2 (Menggunakan File Lokal):**
```bash
sudo ./add-package-fedora.sh ~/Downloads/my-package-1.0.0.rpm
```
Skrip ini secara otomatis akan:
1. Mengunduh file RPM (jika berupa URL) atau menyalinnya (jika berupa berkas lokal) ke direktori `/var/www/repo/fedora/`.
2. Menjalankan perintah `createrepo --update` untuk memperbarui berkas metadata di folder `repodata/` agar client mengetahui adanya paket baru.

---

## 3. Konfigurasi Web Server (Nginx)

Agar repositori dapat diakses oleh komputer client, Anda harus menyajikan direktori `/var/www/repo` menggunakan web server seperti Nginx.

Buat file konfigurasi virtual host Nginx baru, misalnya di `/etc/nginx/sites-available/repo.conf`:

```nginx
server {
    listen 80;
    server_name deps.oktanio.dev; # Ubah domain jika pindah host

    root /var/www/repo;
    autoindex on; # Wajib diaktifkan agar direktori dapat dilist oleh package manager

    location / {
        try_files $uri $uri/ =404;
    }
}
```

Aktifkan konfigurasi dan restart Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/repo.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 4. Konfigurasi di Sisi Client (Pengguna Repositori)

Setelah web server berjalan di `https://deps.oktanio.dev`, client dapat mendaftarkan repositori tersebut dengan cara berikut:

### A. Untuk Client Ubuntu/Debian
Buat file source list baru di `/etc/apt/sources.list.d/deps-oktanio.list`:
```bash
echo "deb [trusted=yes] https://deps.oktanio.dev/debian stable main" | sudo tee /etc/apt/sources.list.d/deps-oktanio.list
```
*Catatan: Opsi `[trusted=yes]` digunakan jika repositori tidak ditandatangani dengan kunci GPG.*

Perbarui indeks paket Anda:
```bash
sudo apt update
```
Sekarang Anda siap memasang aplikasi dari repositori tersebut menggunakan `sudo apt install <nama-paket>`.

### B. Untuk Client Fedora
Client Fedora dapat dengan mudah mengunduh file konfigurasi repo yang sudah otomatis terbuat saat menjalankan `setup-fedora.sh`:
```bash
sudo curl -sL https://deps.oktanio.dev/fedora/deps-oktanio.repo -o /etc/yum.repos.d/deps-oktanio.repo
```

Atau mendaftarkannya secara manual dengan membuat file `/etc/yum.repos.d/deps-oktanio.repo`:
```ini
[deps-oktanio]
name=Deps Oktanio Repository
baseurl=https://deps.oktanio.dev/fedora
enabled=1
gpgcheck=0
```

Perbarui cache repositori:
```bash
sudo dnf makecache
```
Sekarang Anda siap memasang aplikasi menggunakan `sudo dnf install <nama-paket>`.

---

## 5. Keamanan & Tanda Tangan GPG (Opsional namun Direkomendasikan)

Secara default, instalasi di atas menggunakan konfigurasi tanpa tanda tangan kunci (unsigned / untrusted). Untuk produksi, sangat direkomendasikan menandatangani repositori menggunakan GPG.

### Langkah-langkah Pembuatan Kunci GPG:
1. Buat kunci GPG baru di server repositori:
   ```bash
   gpg --generate-key
   ```
2. Ekspor public key ke root repositori Anda agar client bisa mengunduhnya:
   ```bash
   gpg --export --armor "Nama Kunci Anda" > /var/www/repo/public.key
   ```

### Menandatangani Repositori Ubuntu/Debian:
Setelah menambahkan paket, lakukan penandatanganan pada berkas `Release`:
```bash
cd /var/www/repo/debian
gpg --yes --clearsign -o dists/stable/InRelease dists/stable/Release
gpg --yes -abs -o dists/stable/Release.gpg dists/stable/Release
```
**Konfigurasi Client Ubuntu (Aman):**
```bash
# Unduh & daftarkan public key
curl -fsSL https://deps.oktanio.dev/public.key | sudo gpg --dearmor -o /etc/apt/keyrings/deps-oktanio.gpg

# Daftarkan repositori menggunakan signed-by
echo "deb [signed-by=/etc/apt/keyrings/deps-oktanio.gpg] https://deps.oktanio.dev/debian stable main" | sudo tee /etc/apt/sources.list.d/deps-oktanio.list
sudo apt update
```

### Menandatangani Repositori Fedora:
Tandatangani file metadata `repomd.xml` setelah menjalankan `createrepo`:
```bash
cd /var/www/repo/fedora
gpg --detach-sign --armor repodata/repomd.xml
```
*(Ini akan menghasilkan berkas `repodata/repomd.xml.asc`)*

**Konfigurasi Client Fedora (Aman):**
Ubah file `/etc/yum.repos.d/deps-oktanio.repo` menjadi:
```ini
[deps-oktanio]
name=Deps Oktanio Repository
baseurl=https://deps.oktanio.dev/fedora
enabled=1
gpgcheck=1
gpgkey=https://deps.oktanio.dev/public.key
```
Ketika pertama kali dnf mendownload paket, dnf akan mengunduh kunci GPG dan memverifikasi integritas repositori serta paket di dalamnya.
