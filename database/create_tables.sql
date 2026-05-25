/* =========================================================
   FILE  : supervisor_dashboard_views.sql
   TUJUAN: VIEW KHUSUS SUPERVISOR & DASHBOARD
   DATA  : ecommerce_cleaned
   CATATAN:
   - Semua view hanya menggunakan data VALID (is_valid = 1)
   - Aman langsung di-run
   ========================================================= */


/* =========================================================
   1. RINGKASAN UMUM DATA
   ========================================================= */
CREATE OR REPLACE VIEW vw_supervisor_ringkasan_umum AS
SELECT
    COUNT(*) AS total_data,
    SUM(is_valid) AS total_data_valid,
    SUM(CASE WHEN is_valid = 0 THEN 1 ELSE 0 END) AS total_data_tidak_valid
FROM ecommerce_cleaned;


/* =========================================================
   2. ALASAN DATA TIDAK VALID
   ========================================================= */
CREATE OR REPLACE VIEW vw_supervisor_alasan_tidak_valid AS
SELECT
    alasan_tidak_valid,
    COUNT(*) AS jumlah
FROM ecommerce_cleaned
WHERE is_valid = 0
GROUP BY alasan_tidak_valid
ORDER BY jumlah DESC;


/* =========================================================
   3. SEBARAN DATA VALID PER LOKASI
   ========================================================= */
CREATE OR REPLACE VIEW vw_supervisor_sebaran_lokasi AS
SELECT
    lokasi,
    COUNT(*) AS jumlah_data_valid
FROM ecommerce_cleaned
WHERE is_valid = 1
  AND lokasi IS NOT NULL
GROUP BY lokasi
ORDER BY jumlah_data_valid DESC;


/* =========================================================
   4. SEBARAN KATEGORI DATA VALID
   ========================================================= */
CREATE OR REPLACE VIEW vw_supervisor_sebaran_kategori AS
SELECT
    kategori,
    COUNT(*) AS jumlah_data_valid
FROM ecommerce_cleaned
WHERE is_valid = 1
  AND kategori IS NOT NULL
GROUP BY kategori
ORDER BY jumlah_data_valid DESC;


/* =========================================================
   5. KONDISI BARANG (BARU / BEKAS)
   ========================================================= */
CREATE OR REPLACE VIEW vw_supervisor_kondisi_barang AS
SELECT
    kondisi,
    COUNT(*) AS jumlah
FROM ecommerce_cleaned
WHERE is_valid = 1
  AND kondisi IS NOT NULL
GROUP BY kondisi;


/* =========================================================
   6. SEBARAN PEDAGANG vs BUKAN PEDAGANG (TOTAL)
   ========================================================= */
CREATE OR REPLACE VIEW vw_supervisor_konsentrasi_pedagang AS
SELECT
    CASE
        WHEN status_pedagang = 1 THEN 'Pedagang'
        ELSE 'Bukan Pedagang'
    END AS tipe_penjual,
    COUNT(*) AS jumlah,
    ROUND(
        COUNT(*) / (SELECT COUNT(*) FROM ecommerce_cleaned WHERE is_valid = 1) * 100,
        2
    ) AS persen
FROM ecommerce_cleaned
WHERE is_valid = 1
GROUP BY status_pedagang;


/* =========================================================
   7. PEDAGANG vs BUKAN PEDAGANG PER LOKASI
   ========================================================= */
CREATE OR REPLACE VIEW vw_supervisor_pedagang_per_lokasi AS
SELECT
    lokasi,
    SUM(CASE WHEN status_pedagang = 1 THEN 1 ELSE 0 END) AS jumlah_pedagang,
    SUM(CASE WHEN status_pedagang = 0 THEN 1 ELSE 0 END) AS jumlah_bukan_pedagang,
    COUNT(*) AS total_data_valid
FROM ecommerce_cleaned
WHERE is_valid = 1
  AND lokasi IS NOT NULL
  AND status_pedagang IS NOT NULL
GROUP BY lokasi
ORDER BY total_data_valid DESC;


/* =========================================================
   8. PEDAGANG vs BUKAN PEDAGANG PER KATEGORI
   ========================================================= */
CREATE OR REPLACE VIEW vw_supervisor_pedagang_per_kategori AS
SELECT
    kategori,
    SUM(CASE WHEN status_pedagang = 1 THEN 1 ELSE 0 END) AS jumlah_pedagang,
    SUM(CASE WHEN status_pedagang = 0 THEN 1 ELSE 0 END) AS jumlah_bukan_pedagang,
    COUNT(*) AS total_data_valid
FROM ecommerce_cleaned
WHERE is_valid = 1
  AND kategori IS NOT NULL
  AND status_pedagang IS NOT NULL
GROUP BY kategori
ORDER BY total_data_valid DESC;


/* =========================================================
   9. TOP 5 LOKASI PALING AKTIF
   ========================================================= */
CREATE OR REPLACE VIEW vw_supervisor_top_lokasi AS
SELECT
    lokasi,
    COUNT(*) AS jumlah_data_valid
FROM ecommerce_cleaned
WHERE is_valid = 1
  AND lokasi IS NOT NULL
GROUP BY lokasi
ORDER BY jumlah_data_valid DESC
LIMIT 5;


/* =========================================================
   10. DIVERSIFIKASI KATEGORI PER LOKASI
   ========================================================= */
CREATE OR REPLACE VIEW vw_supervisor_diversifikasi_kategori AS
SELECT
    lokasi,
    COUNT(DISTINCT kategori) AS jumlah_kategori
FROM ecommerce_cleaned
WHERE is_valid = 1
  AND lokasi IS NOT NULL
  AND kategori IS NOT NULL
GROUP BY lokasi
ORDER BY jumlah_kategori DESC;
