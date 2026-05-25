# Deploy Dashboard Ke Railway

Panduan ini dipakai untuk membuat dashboard Django + MySQL bisa dibuka lewat link publik Railway.

## 1. Buat Project Railway

1. Buka `https://railway.com`.
2. Login menggunakan GitHub.
3. Klik **New Project**.
4. Pilih **Deploy from GitHub repo**.
5. Pilih repository `korison230603/dashboard-ecommerce-sulteng`.

## 2. Tambahkan Database MySQL

1. Di halaman project Railway, klik **+ New**.
2. Pilih **Database**.
3. Pilih **MySQL**.
4. Railway akan membuat variabel database seperti `MYSQLHOST`, `MYSQLPORT`, `MYSQLUSER`, `MYSQLPASSWORD`, dan `MYSQLDATABASE`.

## 3. Atur Environment Variables Di Service Django

Masuk ke service dashboard, buka tab **Variables**, lalu tambahkan:

```text
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=isi-dengan-secret-key-panjang
DJANGO_ALLOWED_HOSTS=.up.railway.app
DJANGO_CSRF_TRUSTED_ORIGINS=https://*.up.railway.app
```

Jika Railway memberi domain lain, tambahkan domain itu ke `DJANGO_ALLOWED_HOSTS` dan `DJANGO_CSRF_TRUSTED_ORIGINS`.

## 4. Hubungkan Variabel MySQL Ke Service Django

Pastikan service Django bisa membaca variabel MySQL. Jika variabel MySQL belum otomatis tersedia di service Django, tambahkan manual di service Django:

```text
MYSQLHOST=...
MYSQLPORT=...
MYSQLUSER=...
MYSQLPASSWORD=...
MYSQLDATABASE=...
```

Nilainya bisa disalin dari service MySQL di Railway.

## 5. Import Database

Export database dari komputer lokal:

```powershell
mysqldump -u newuser -p ecommerce_project > ecommerce_project.sql
```

Import ke MySQL Railway memakai host, port, user, password, dan database dari Railway.

## 6. Deploy

Setelah variables dan database siap, buka service dashboard lalu klik **Deploy** atau **Redeploy**.

Jika berhasil, Railway akan memberi link publik untuk dashboard.
