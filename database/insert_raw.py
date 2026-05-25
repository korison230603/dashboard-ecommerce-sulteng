from database.connect import get_connection
from datetime import datetime

def insert_raw(data):
    conn = get_connection()
    cursor = conn.cursor()

    sql = """
        INSERT IGNORE INTO ecommerce_raw (
            id_produk,
            nama_produk,
            deskripsi,
            toko,
            harga,
            lokasi,
            url,
            region,
            scraped_at
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """

    values = (
        data.get("id_produk"),
        data.get("nama_produk"),
        data.get("deskripsi"),
        data.get("toko"),
        data.get("harga"),
        data.get("lokasi"),
        data.get("url"),
        data.get("region"),
        data.get("scraped_at") or datetime.now()
    )

    cursor.execute(sql, values)
    conn.commit()
    cursor.close()
    conn.close()


# ================= GET EXISTING IDS =================
def get_existing_ids():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id_produk FROM ecommerce_raw")
    ids = {row[0] for row in cursor.fetchall()}

    cursor.close()
    conn.close()
    return ids
