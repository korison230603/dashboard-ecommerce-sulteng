# Dashboard E-commerce Sulawesi Tengah

Dashboard Django untuk menampilkan ringkasan dan analisis data platform digital di Sulawesi Tengah, termasuk Tokopedia, Shopee, Lazada, Blibli, Facebook Marketplace, komunitas digital, dan GrabFood.

## Fitur

- Ringkasan sebaran toko/akun berdasarkan kabupaten/kota.
- Dashboard per platform dengan filter, grafik, tabel, dan export data.
- Dashboard GrabFood dengan peta titik merchant, status operasional, dan export data.
- Export data tabel ke Excel, CSV, dan JSON.
- Konfigurasi rahasia melalui file `.env`.

## Menjalankan Project

1. Clone repository:

```powershell
git clone https://github.com/korison230603/dashboard-ecommerce-sulteng.git
cd dashboard-ecommerce-sulteng
```

2. Buat virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

3. Install dependency:

```powershell
pip install -r requirements.txt
```

4. Buat file `.env` dari contoh:

```powershell
copy .env.example .env
```

5. Isi konfigurasi database dan secret key di `.env`.

6. Jalankan server:

```powershell
cd ecommerce_dashboard
python manage.py runserver
```

7. Buka dashboard di browser:

```text
http://127.0.0.1:8000/
```

## Catatan

File `.env` tidak di-upload ke GitHub karena berisi konfigurasi rahasia seperti password database dan secret key.
