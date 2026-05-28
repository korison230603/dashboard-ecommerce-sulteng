import json
from time import monotonic

from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect, render


# ===============================
# HELPER FUNCTION
# ===============================
SUMMARY_CACHE_SECONDS = 600
SUMMARY_RESPONSE_CACHE = {}
FILTER_OPTIONS_CACHE = {"expires_at": 0, "data": None}

DEFAULT_FILTER_OPTIONS = {
    "platform": [
        {"value": "Tokopedia"},
        {"value": "Shopee"},
        {"value": "Lazada"},
        {"value": "Blibli"},
        {"value": "Facebook Marketplace"},
    ],
    "lokasi": [],
    "kategori": [],
}

RESTRICTED_SECTIONS = {
    "facebook": "Facebook Marketplace",
    "ecommerce": "Facebook Marketplace",
    "tokopedia": "Tokopedia",
    "shopee": "Shopee",
    "lazada": "Lazada",
    "blibli": "Blibli",
    "grabfood": "GrabFood",
    "komunitas": "Komunitas Digital",
}

DETAIL_ACCESS_SESSION_KEY = "dashboard_detail_access"
DETAIL_SECTION_PATHS = {
    "Facebook Marketplace": "/facebook/",
    "Tokopedia": "/tokopedia/",
    "Shopee": "/shopee/",
    "Lazada": "/lazada/",
    "Blibli": "/blibli/",
    "GrabFood": "/grabfood/",
    "Komunitas Digital": "/komunitas/",
}


def restricted_context(section=None):
    section_name = section or "Platform detail"
    return {
        "section_name": section_name,
        "target_path": DETAIL_SECTION_PATHS.get(section_name, "/"),
        "restricted_message": (
            "Akses detail dibatasi untuk menjaga privasi data pelaku usaha. "
            "Publik hanya dapat melihat ringkasan agregat pada halaman utama."
        ),
    }


def privacy_notice_page(request, section=None):
    selected_section = section or request.GET.get("section") or "Platform detail"
    context = restricted_context(selected_section)

    if request.method == "POST":
        access_code = request.POST.get("access_code", "").strip()
        if access_code == settings.DASHBOARD_ACCESS_CODE:
            if hasattr(request, "session"):
                request.session[DETAIL_ACCESS_SESSION_KEY] = True
            return redirect(context["target_path"])

        context["access_error"] = (
            "Kode akses tidak sesuai. Periksa kembali kode dari pemilik dashboard "
            "atau ajukan akses resmi melalui email."
        )

    return render(request, "restricted.html", context)


def has_detail_access(request):
    return bool(getattr(request, "session", {}).get(DETAIL_ACCESS_SESSION_KEY))


def render_protected_page(request, section_key, template_name, context=None):
    if not has_detail_access(request):
        return privacy_notice_page(request, RESTRICTED_SECTIONS[section_key])

    return render(request, template_name, context or {})


def require_detail_access(request, section):
    if has_detail_access(request):
        return None

    return restricted_api_response(section)


def restricted_api_response(section):
    return JsonResponse(
        {
            "status": "restricted",
            "section": section,
            "message": (
                "Akses data detail dibatasi untuk menjaga privasi data pelaku usaha. "
                "Silakan gunakan ringkasan agregat pada halaman utama."
            ),
        },
        status=403,
    )


def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def escape_sql_percent_literals(query):
    escaped = []
    in_string = False
    index = 0

    while index < len(query):
        char = query[index]
        next_char = query[index + 1] if index + 1 < len(query) else ""

        if char == "'":
            escaped.append(char)
            if in_string and next_char == "'":
                escaped.append(next_char)
                index += 2
                continue
            in_string = not in_string
            index += 1
            continue

        if char == "%":
            if in_string:
                escaped.append("%%")
            elif next_char == "s":
                escaped.append("%s")
                index += 2
                continue
            else:
                escaped.append("%%")
            index += 1
            continue

        escaped.append(char)
        index += 1

    return "".join(escaped)


def query_view(query, params=None):
    with connection.cursor() as cursor:
        if not params:
            cursor.execute(query)
        else:
            safe_query = escape_sql_percent_literals(query)
            cursor.execute(safe_query, params)
        return dictfetchall(cursor)


def make_request_cache_key(request, include_full):
    items = []
    for key in sorted(request.GET.keys()):
        items.append((key, tuple(sorted(request.GET.getlist(key)))))
    return include_full, tuple(items)


def get_summary_cache(key):
    cached = SUMMARY_RESPONSE_CACHE.get(key)
    if not cached:
        return None

    expires_at, data = cached
    if expires_at <= monotonic():
        SUMMARY_RESPONSE_CACHE.pop(key, None)
        return None

    return data


def set_summary_cache(key, data):
    SUMMARY_RESPONSE_CACHE[key] = (monotonic() + SUMMARY_CACHE_SECONDS, data)
    return data


def minimal_filter_options():
    cached = FILTER_OPTIONS_CACHE.get("data")
    return cached or DEFAULT_FILTER_OPTIONS


def percentile(sorted_values, fraction):
    if not sorted_values:
        return 0

    position = (len(sorted_values) - 1) * fraction
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)
    weight = position - lower_index

    if lower_index == upper_index:
        return round(sorted_values[lower_index], 2)

    return round(
        (sorted_values[lower_index] * (1 - weight)) + (sorted_values[upper_index] * weight),
        2,
    )


def summarize_price_values(values):
    clean_values = sorted(
        float(value)
        for value in values
        if value is not None and float(value) > 0
    )

    if not clean_values:
        return {
            "jumlah_harga_valid": 0,
            "harga_median": 0,
            "harga_p95": 0,
            "rata_rata_harga_normal": 0,
        }

    harga_p95 = percentile(clean_values, 0.95)
    trimmed_values = [value for value in clean_values if value <= harga_p95] or clean_values

    return {
        "jumlah_harga_valid": len(clean_values),
        "harga_median": percentile(clean_values, 0.5),
        "harga_p95": harga_p95,
        "rata_rata_harga_normal": round(sum(trimmed_values) / len(trimmed_values), 2),
    }


def build_ecommerce_price_stats(base_query=None, params=None):
    source_query = base_query or f"SELECT * FROM ({ALL_ECOMMERCE_UNION_QUERY}) all_ecommerce"
    rows = query_view(
        f"""
        SELECT marketplace, harga
        FROM ({source_query}) price_source
        WHERE harga IS NOT NULL AND harga > 0
        ORDER BY marketplace ASC, harga ASC
        """,
        params,
    )

    all_prices = []
    grouped_prices = {}

    for row in rows:
        marketplace = row.get("marketplace") or "Tidak diketahui"
        harga = row.get("harga")
        all_prices.append(harga)
        grouped_prices.setdefault(marketplace, []).append(harga)

    marketplace_stats = [
        {"marketplace": marketplace, **summarize_price_values(values)}
        for marketplace, values in grouped_prices.items()
    ]
    marketplace_stats.sort(key=lambda row: row["marketplace"])

    return {
        "overall": summarize_price_values(all_prices),
        "marketplace": marketplace_stats,
    }


def request_list(request, key):
    values = []
    for raw_value in request.GET.getlist(key):
        values.extend(str(raw_value).split(","))
    return [value.strip() for value in values if value and value.strip()]


def build_ecommerce_filter_source(request):
    allowed_platforms = {
        "Tokopedia",
        "Shopee",
        "Lazada",
        "Blibli",
        "Facebook Marketplace",
    }

    filters = []
    params = []

    platforms = [value for value in request_list(request, "platform") if value in allowed_platforms]
    locations = request_list(request, "lokasi")
    categories = request_list(request, "kategori")
    lokasi_normal = normalized_location_sql("lokasi")
    kategori_normal = normalized_category_sql("kategori")

    if platforms:
        filters.append(f"marketplace IN ({', '.join(['%s'] * len(platforms))})")
        params.extend(platforms)

    if locations:
        filters.append(f"{lokasi_normal} IN ({', '.join(['%s'] * len(locations))})")
        params.extend(locations)

    if categories:
        filters.append(f"{kategori_normal} IN ({', '.join(['%s'] * len(categories))})")
        params.extend(categories)

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    source_query = f"SELECT * FROM ({ALL_ECOMMERCE_UNION_QUERY}) all_ecommerce {where_clause}"
    return source_query, params


def normalized_category_sql(field="kategori"):
    value = f"LOWER(TRIM(COALESCE({field}, '')))"
    return f"""
        CASE
            WHEN {value} = '' OR {value} LIKE '%tidak diketahui%' THEN 'Tidak diketahui'
            WHEN {value} LIKE '%fashion%' OR {value} LIKE '%pakaian%' OR {value} LIKE '%baju%' OR {value} LIKE '%sepatu%' OR {value} LIKE '%tas%' OR {value} LIKE '%aksesoris%' THEN 'Fashion & Aksesoris'
            WHEN {value} LIKE '%kecantikan%' OR {value} LIKE '%perawatan%' OR {value} LIKE '%beauty%' OR {value} LIKE '%kosmetik%' THEN 'Kecantikan & Perawatan'
            WHEN {value} LIKE '%elektronik%' OR {value} LIKE '%gadget%' OR {value} LIKE '%handphone%' OR {value} LIKE '%hp%' OR {value} LIKE '%komputer%' THEN 'Elektronik & Gadget'
            WHEN {value} LIKE '%makanan%' OR {value} LIKE '%minuman%' OR {value} LIKE '%food%' OR {value} LIKE '%kuliner%' THEN 'Makanan & Minuman'
            WHEN {value} LIKE '%kendaraan%' OR {value} LIKE '%mobil%' OR {value} LIKE '%motor%' OR {value} LIKE '%otomotif%' THEN 'Kendaraan & Otomotif'
            WHEN {value} LIKE '%rumah%' OR {value} LIKE '%properti%' OR {value} LIKE '%furnitur%' OR {value} LIKE '%dekorasi%' THEN 'Rumah, Properti & Furnitur'
            WHEN {value} LIKE '%kesehatan%' OR {value} LIKE '%obat%' OR {value} LIKE '%medis%' THEN 'Kesehatan'
            WHEN {value} LIKE '%bayi%' OR {value} LIKE '%anak%' OR {value} LIKE '%mainan%' THEN 'Bayi, Anak & Mainan'
            WHEN {value} LIKE '%olahraga%' OR {value} LIKE '%hobi%' THEN 'Olahraga & Hobi'
            WHEN {value} LIKE '%jasa%' OR {value} LIKE '%layanan%' THEN 'Jasa & Layanan'
            ELSE CONCAT(UCASE(LEFT(TRIM({field}), 1)), SUBSTRING(LOWER(TRIM({field})), 2))
        END
    """


def normalized_location_sql(field="lokasi"):
    value = f"LOWER(TRIM(COALESCE({field}, '')))"
    return f"""
        CASE
            WHEN {value} = '' OR {value} LIKE '%tidak diketahui%' THEN 'Tidak diketahui'
            WHEN {value} LIKE '%palu%' THEN 'Palu'
            WHEN {value} LIKE '%parigi%' THEN 'Parigi Moutong'
            WHEN {value} LIKE '%morowali utara%' THEN 'Morowali Utara'
            WHEN {value} LIKE '%morowali%' THEN 'Morowali'
            WHEN {value} LIKE '%toli%' THEN 'Toli Toli'
            WHEN {value} LIKE '%banggai laut%' THEN 'Banggai Laut'
            WHEN {value} LIKE '%banggai kepulauan%' THEN 'Banggai Kepulauan'
            WHEN {value} LIKE '%banggai%' THEN 'Banggai'
            WHEN {value} LIKE '%buol%' THEN 'Buol'
            WHEN {value} LIKE '%donggala%' THEN 'Donggala'
            WHEN {value} LIKE '%poso%' THEN 'Poso'
            WHEN {value} LIKE '%sigi%' THEN 'Sigi'
            WHEN {value} LIKE '%tojo%' THEN 'Tojo Una-Una'
            ELSE CONCAT(UCASE(LEFT(TRIM({field}), 1)), SUBSTRING(LOWER(TRIM({field})), 2))
        END
    """


def build_ecommerce_filter_options():
    if FILTER_OPTIONS_CACHE["data"] and FILTER_OPTIONS_CACHE["expires_at"] > monotonic():
        return FILTER_OPTIONS_CACHE["data"]

    lokasi_normal = normalized_location_sql("lokasi")
    kategori_normal = normalized_category_sql("kategori")

    data = {
        "platform": query_view(
            f"""
            SELECT DISTINCT marketplace AS value
            FROM ({ALL_ECOMMERCE_UNION_QUERY}) all_ecommerce
            ORDER BY marketplace ASC
            """
        ),
        "lokasi": query_view(
            f"""
            SELECT DISTINCT {lokasi_normal} AS value
            FROM ({ALL_ECOMMERCE_UNION_QUERY}) all_ecommerce
            WHERE lokasi IS NOT NULL AND TRIM(lokasi) <> ''
            ORDER BY value ASC
            """
        ),
        "kategori": query_view(
            f"""
            SELECT DISTINCT {kategori_normal} AS value
            FROM ({ALL_ECOMMERCE_UNION_QUERY}) all_ecommerce
            WHERE kategori IS NOT NULL AND TRIM(kategori) <> ''
            ORDER BY value ASC
            """
        ),
    }
    FILTER_OPTIONS_CACHE["data"] = data
    FILTER_OPTIONS_CACHE["expires_at"] = monotonic() + SUMMARY_CACHE_SECONDS
    return data


def build_ecommerce_summary_response(request, include_full=True):
    cache_key = make_request_cache_key(request, include_full)
    cached_response = get_summary_cache(cache_key)
    if cached_response is not None:
        return cached_response

    source_query, params = build_ecommerce_filter_source(request)
    kategori_normal = normalized_category_sql("kategori")
    lokasi_normal = normalized_location_sql("lokasi")
    marketplace_rows = query_view(
        f"""
        SELECT
            marketplace,
            COUNT(*) AS total_produk,
            COUNT(DISTINCT NULLIF(TRIM(toko), '')) AS total_toko,
            COUNT(DISTINCT kategori) AS total_kategori,
            COUNT(DISTINCT lokasi) AS total_lokasi,
            ROUND(AVG(NULLIF(harga, 0)), 2) AS rata_rata_harga,
            MIN(NULLIF(harga, 0)) AS harga_min,
            MAX(NULLIF(harga, 0)) AS harga_max
        FROM ({source_query}) filtered_ecommerce
        GROUP BY marketplace
        ORDER BY total_produk DESC, marketplace ASC
        """,
        params,
    )

    if include_full:
        overview_rows = query_view(
            f"""
            SELECT
                COUNT(*) AS total_produk,
                COUNT(DISTINCT CASE WHEN toko IS NOT NULL THEN CONCAT(marketplace, ':', toko) END) AS total_toko,
                COUNT(DISTINCT kategori) AS total_kategori,
                COUNT(DISTINCT lokasi) AS total_lokasi,
                ROUND(AVG(NULLIF(harga, 0)), 2) AS rata_rata_harga,
                MIN(NULLIF(harga, 0)) AS harga_min,
                MAX(NULLIF(harga, 0)) AS harga_max
            FROM ({source_query}) filtered_ecommerce
            """,
            params,
        )
    else:
        overview_rows = [{
            "total_produk": sum(row["total_produk"] or 0 for row in marketplace_rows),
            "total_toko": sum(row["total_toko"] or 0 for row in marketplace_rows),
            "total_kategori": 0,
            "total_lokasi": 0,
            "rata_rata_harga": 0,
            "harga_min": 0,
            "harga_max": 0,
        }]

    data = {
        "overview": overview_rows,
        "marketplace": marketplace_rows,
        "filter_options": build_ecommerce_filter_options() if include_full else minimal_filter_options(),
    }

    if not include_full:
        data["facebook"] = build_facebook_summary()
        data["grabfood"] = build_grabfood_summary()
        return set_summary_cache(cache_key, data)

    data.update({
        "kategori": query_view(
            f"""
            SELECT
                {kategori_normal} AS kategori,
                marketplace,
                COUNT(*) AS jumlah_produk,
                COUNT(DISTINCT CASE WHEN toko IS NOT NULL THEN CONCAT(marketplace, ':', toko) END) AS jumlah_toko
            FROM ({source_query}) filtered_ecommerce
            GROUP BY {kategori_normal}, marketplace
            ORDER BY jumlah_toko DESC, jumlah_produk DESC, kategori ASC, marketplace ASC
            LIMIT 80
            """,
            params,
        ),
        "toko_kategori": query_view(
            f"""
            SELECT
                {kategori_normal} AS kategori,
                COUNT(DISTINCT CASE WHEN toko IS NOT NULL THEN CONCAT(marketplace, ':', toko) END) AS jumlah_toko,
                COUNT(*) AS jumlah_produk,
                COUNT(DISTINCT marketplace) AS jumlah_marketplace
            FROM ({source_query}) filtered_ecommerce
            GROUP BY {kategori_normal}
            ORDER BY jumlah_toko DESC, jumlah_produk DESC, kategori ASC
            LIMIT 10
            """,
            params,
        ),
        "lokasi": query_view(
            f"""
            SELECT
                {lokasi_normal} AS lokasi,
                marketplace,
                COUNT(DISTINCT CASE WHEN toko IS NOT NULL THEN CONCAT(marketplace, ':', toko) END) AS jumlah_toko,
                COUNT(*) AS jumlah_produk
            FROM ({source_query}) filtered_ecommerce
            GROUP BY {lokasi_normal}, marketplace
            ORDER BY jumlah_toko DESC, jumlah_produk DESC, lokasi ASC, marketplace ASC
            """,
            params,
        ),
        "harga": query_view(
            f"""
            SELECT
                rentang_harga,
                COUNT(*) AS jumlah
            FROM (
                SELECT
                    CASE
                        WHEN harga IS NULL OR harga <= 0 THEN 'Tidak diketahui'
                        WHEN harga < 50000 THEN '< Rp50 rb'
                        WHEN harga < 100000 THEN 'Rp50 rb - Rp99 rb'
                        WHEN harga < 250000 THEN 'Rp100 rb - Rp249 rb'
                        WHEN harga < 500000 THEN 'Rp250 rb - Rp499 rb'
                        WHEN harga < 1000000 THEN 'Rp500 rb - Rp999 rb'
                        WHEN harga < 2500000 THEN 'Rp1 jt - Rp2,4 jt'
                        WHEN harga < 5000000 THEN 'Rp2,5 jt - Rp4,9 jt'
                        WHEN harga < 10000000 THEN 'Rp5 jt - Rp9,9 jt'
                        WHEN harga < 25000000 THEN 'Rp10 jt - Rp24,9 jt'
                        WHEN harga < 50000000 THEN 'Rp25 jt - Rp49,9 jt'
                        ELSE '>= Rp50 jt'
                    END AS rentang_harga,
                    CASE
                        WHEN harga IS NULL OR harga <= 0 THEN 0
                        WHEN harga < 50000 THEN 1
                        WHEN harga < 100000 THEN 2
                        WHEN harga < 250000 THEN 3
                        WHEN harga < 500000 THEN 4
                        WHEN harga < 1000000 THEN 5
                        WHEN harga < 2500000 THEN 6
                        WHEN harga < 5000000 THEN 7
                        WHEN harga < 10000000 THEN 8
                        WHEN harga < 25000000 THEN 9
                        WHEN harga < 50000000 THEN 10
                        ELSE 11
                    END AS urutan
                FROM ({source_query}) filtered_ecommerce
                WHERE punya_harga = 1
            ) distribusi_harga
            GROUP BY rentang_harga, urutan
            ORDER BY urutan ASC
            """,
            params,
        ),
        "price_stats": build_ecommerce_price_stats(source_query, params),
        "dominant_category": query_view(
            f"""
            SELECT marketplace, kategori, jumlah_produk, jumlah_toko
            FROM (
                SELECT
                    marketplace,
                    {kategori_normal} AS kategori,
                    COUNT(*) AS jumlah_produk,
                    COUNT(DISTINCT NULLIF(TRIM(toko), '')) AS jumlah_toko,
                    ROW_NUMBER() OVER (
                        PARTITION BY marketplace
                        ORDER BY COUNT(DISTINCT NULLIF(TRIM(toko), '')) DESC, COUNT(*) DESC, {kategori_normal} ASC
                    ) AS urutan
                FROM ({source_query}) filtered_ecommerce
                GROUP BY marketplace, {kategori_normal}
            ) ranked_category
            WHERE urutan = 1
            ORDER BY marketplace ASC
            """,
            params,
        ),
        "dominant_location": query_view(
            f"""
            SELECT marketplace, lokasi, jumlah_produk, jumlah_toko
            FROM (
                SELECT
                    marketplace,
                    {lokasi_normal} AS lokasi,
                    COUNT(*) AS jumlah_produk,
                    COUNT(DISTINCT NULLIF(TRIM(toko), '')) AS jumlah_toko,
                    ROW_NUMBER() OVER (
                        PARTITION BY marketplace
                        ORDER BY COUNT(DISTINCT NULLIF(TRIM(toko), '')) DESC, COUNT(*) DESC, {lokasi_normal} ASC
                    ) AS urutan
                FROM ({source_query}) filtered_ecommerce
                GROUP BY marketplace, {lokasi_normal}
            ) ranked_location
            WHERE urutan = 1
            ORDER BY marketplace ASC
            """,
            params,
        ),
        "facebook": build_facebook_summary(),
        "grabfood": build_grabfood_summary(),
    })

    return set_summary_cache(cache_key, data)


def normalize_community_rows(rows):
    normalized_rows = []

    for row in rows:
        normalized = dict(row)
        author = str(normalized.get("Author") or "").strip().lower()

        # Facebook anonymous participants should not be treated as fictitious names.
        if author == "peserta anonim":
            normalized["flag_author"] = "bukan_nama_fiktif"

        normalized_rows.append(normalized)

    return normalized_rows


def community_author_key(row):
    author_id = str(row.get("author_id") or "").strip()
    if author_id:
        return f"id:{author_id}"

    author = str(row.get("Author") or "").strip().lower()
    if author:
        return f"name:{author}"

    return f"post:{row.get('PostID') or ''}"


def community_category(row):
    return str(row.get("category") or "").strip().lower()


def community_sort_text(value):
    return str(value or "").strip().lower()


def community_datetime_key(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value or "")


def fetch_community_source_rows():
    return query_view(
        """
        SELECT
            PostID,
            author_id,
            Author,
            content,
            comments,
            flag_author,
            Posted_At,
            group_name,
            category
        FROM komunitas_cleaned
        """
    )


def build_community_dataset():
    rows_by_author = {}

    for row in fetch_community_source_rows():
        author_key = community_author_key(row)
        rows_by_author.setdefault(author_key, []).append(dict(row))

    master_rows = []
    intensity_rows = []

    for author_rows in rows_by_author.values():
        kategori_final = (
            "pedagang"
            if any(community_category(row) == "pedagang" for row in author_rows)
            else "non-dagang"
        )
        representative_row = max(
            author_rows,
            key=lambda row: (
                1 if community_category(row) == "pedagang" else 0,
                community_datetime_key(row.get("Posted_At")),
                str(row.get("PostID") or ""),
            ),
        )

        master_row = dict(representative_row)
        master_row["kategori_final"] = kategori_final
        master_rows.append(master_row)

        intensity_rows.append({
            "author_id": representative_row.get("author_id"),
            "Author": representative_row.get("Author"),
            "jumlah_post": len(author_rows),
            "kategori_final": kategori_final,
        })

    master_rows = normalize_community_rows(master_rows)
    intensity_rows = normalize_community_rows(intensity_rows)

    master_rows.sort(key=lambda row: community_sort_text(row.get("Author")))
    master_rows.sort(key=lambda row: community_datetime_key(row.get("Posted_At")), reverse=True)

    intensity_rows.sort(key=lambda row: community_sort_text(row.get("Author")))
    intensity_rows.sort(key=lambda row: int(row.get("jumlah_post") or 0), reverse=True)

    group_counts = {}
    overview_counts = {"pedagang": 0, "non-dagang": 0}

    for row in master_rows:
        kategori_final = community_sort_text(row.get("kategori_final")) or "non-dagang"
        overview_counts[kategori_final] = overview_counts.get(kategori_final, 0) + 1

        if kategori_final != "pedagang":
            continue

        group_name = str(row.get("group_name") or "").strip() or "Tidak diketahui"
        group_counts[group_name] = group_counts.get(group_name, 0) + 1

    total_accounts = sum(overview_counts.values())
    overview_rows = []
    for kategori_final in ("pedagang", "non-dagang"):
        jumlah = overview_counts.get(kategori_final, 0)
        persentase = round((jumlah * 100.0 / total_accounts), 2) if total_accounts else 0
        overview_rows.append({
            "kategori_final": kategori_final,
            "jumlah": jumlah,
            "persentase": persentase,
        })

    group_rows = [
        {"group_name": group_name, "jumlah_pedagang": total}
        for group_name, total in group_counts.items()
    ]
    group_rows.sort(key=lambda row: community_sort_text(row.get("group_name")))
    group_rows.sort(key=lambda row: int(row.get("jumlah_pedagang") or 0), reverse=True)

    return {
        "master_rows": master_rows,
        "intensity_rows": intensity_rows,
        "group_rows": group_rows,
        "overview_rows": overview_rows,
    }


TOKOPEDIA_OVERVIEW_QUERY = """
SELECT
    COUNT(*) AS total_produk,
    COUNT(DISTINCT toko) AS total_toko,
    ROUND(AVG(harga), 2) AS rata_rata_harga
FROM tokopedia
"""

TOKOPEDIA_KATEGORI_QUERY = """
SELECT
    COALESCE(NULLIF(TRIM(Kategori), ''), 'Tidak diketahui') AS kategori,
    COUNT(*) AS jumlah
FROM tokopedia
GROUP BY COALESCE(NULLIF(TRIM(Kategori), ''), 'Tidak diketahui')
ORDER BY jumlah DESC, kategori ASC
LIMIT 10
"""

TOKOPEDIA_HARGA_QUERY = """
SELECT
    rentang_harga,
    COUNT(*) AS jumlah
FROM (
    SELECT
        CASE
            WHEN harga IS NULL THEN 'Tidak diketahui'
            WHEN harga < 50000 THEN '< Rp50 rb'
            WHEN harga < 100000 THEN 'Rp50 rb - Rp99 rb'
            WHEN harga < 250000 THEN 'Rp100 rb - Rp249 rb'
            WHEN harga < 500000 THEN 'Rp250 rb - Rp499 rb'
            WHEN harga < 1000000 THEN 'Rp500 rb - Rp999 rb'
            ELSE '>= Rp1 jt'
        END AS rentang_harga,
        CASE
            WHEN harga IS NULL THEN 0
            WHEN harga < 50000 THEN 1
            WHEN harga < 100000 THEN 2
            WHEN harga < 250000 THEN 3
            WHEN harga < 500000 THEN 4
            WHEN harga < 1000000 THEN 5
            ELSE 6
        END AS urutan
    FROM tokopedia
) distribusi_harga
GROUP BY rentang_harga, urutan
ORDER BY urutan
"""

TOKOPEDIA_PRODUK_LOKASI_QUERY = """
SELECT
    COALESCE(NULLIF(TRIM(lokasi), ''), 'Tidak diketahui') AS lokasi,
    COUNT(*) AS jumlah
FROM tokopedia
GROUP BY COALESCE(NULLIF(TRIM(lokasi), ''), 'Tidak diketahui')
ORDER BY jumlah DESC, lokasi ASC
LIMIT 10
"""

TOKOPEDIA_TOKO_LOKASI_QUERY = """
SELECT
    COALESCE(NULLIF(TRIM(lokasi), ''), 'Tidak diketahui') AS lokasi,
    COUNT(DISTINCT toko) AS jumlah
FROM tokopedia
GROUP BY COALESCE(NULLIF(TRIM(lokasi), ''), 'Tidak diketahui')
ORDER BY jumlah DESC, lokasi ASC
LIMIT 10
"""

TOKOPEDIA_TABLE_QUERY = """
SELECT
    id,
    toko,
    produk,
    harga,
    COALESCE(NULLIF(TRIM(lokasi), ''), 'Tidak diketahui') AS lokasi,
    COALESCE(NULLIF(TRIM(Kategori), ''), 'Tidak diketahui') AS kategori,
    url
FROM tokopedia
ORDER BY id DESC
"""

SHOPEE_TABLE_QUERY = """
SELECT
    id,
    Shop_Name AS toko,
    Product_Name AS produk,
    Price AS harga,
    COALESCE(NULLIF(TRIM(Shop_Location), ''), 'Tidak diketahui') AS lokasi,
    COALESCE(NULLIF(TRIM(Category), ''), 'Tidak diketahui') AS kategori,
    Product_URL AS url
FROM shopee
ORDER BY id DESC
"""

LAZADA_TABLE_QUERY = """
SELECT
    id,
    Toko AS toko,
    Produk AS produk,
    Harga AS harga,
    COALESCE(NULLIF(TRIM(Lokasi), ''), 'Tidak diketahui') AS lokasi,
    COALESCE(NULLIF(TRIM(Kategori), ''), 'Tidak diketahui') AS kategori,
    url
FROM lazada
ORDER BY id DESC
"""

BLIBLI_TABLE_QUERY = """
SELECT
    id,
    Toko AS toko,
    Produk AS produk,
    Harga AS harga,
    COALESCE(NULLIF(TRIM(Lokasi), ''), 'Tidak diketahui') AS lokasi,
    COALESCE(NULLIF(TRIM(Kategori), ''), 'Tidak diketahui') AS kategori,
    url
FROM blibli
ORDER BY id DESC
"""

ALL_ECOMMERCE_UNION_QUERY = """
SELECT
    'Tokopedia' AS marketplace,
    NULLIF(TRIM(toko), '') AS toko,
    NULLIF(TRIM(produk), '') AS produk,
    CAST(harga AS DECIMAL(18, 2)) AS harga,
    1 AS punya_harga,
    COALESCE(NULLIF(TRIM(lokasi), ''), 'Tidak diketahui') AS lokasi,
    COALESCE(NULLIF(TRIM(Kategori), ''), 'Tidak diketahui') AS kategori,
    url
FROM tokopedia
UNION ALL
SELECT
    'Shopee' AS marketplace,
    NULLIF(TRIM(Shop_Name), '') AS toko,
    NULLIF(TRIM(Product_Name), '') AS produk,
    CAST(Price AS DECIMAL(18, 2)) AS harga,
    1 AS punya_harga,
    COALESCE(NULLIF(TRIM(Shop_Location), ''), 'Tidak diketahui') AS lokasi,
    COALESCE(NULLIF(TRIM(Category), ''), 'Tidak diketahui') AS kategori,
    Product_URL AS url
FROM shopee
UNION ALL
SELECT
    'Lazada' AS marketplace,
    NULLIF(TRIM(Toko), '') AS toko,
    NULLIF(TRIM(Produk), '') AS produk,
    CAST(Harga AS DECIMAL(18, 2)) AS harga,
    1 AS punya_harga,
    COALESCE(NULLIF(TRIM(Lokasi), ''), 'Tidak diketahui') AS lokasi,
    COALESCE(NULLIF(TRIM(Kategori), ''), 'Tidak diketahui') AS kategori,
    url
FROM lazada
UNION ALL
SELECT
    'Blibli' AS marketplace,
    NULLIF(TRIM(Toko), '') AS toko,
    NULLIF(TRIM(Produk), '') AS produk,
    CAST(Harga AS DECIMAL(18, 2)) AS harga,
    1 AS punya_harga,
    COALESCE(NULLIF(TRIM(Lokasi), ''), 'Tidak diketahui') AS lokasi,
    COALESCE(NULLIF(TRIM(Kategori), ''), 'Tidak diketahui') AS kategori,
    url
FROM blibli
UNION ALL
SELECT
    'Facebook Marketplace' AS marketplace,
    NULLIF(TRIM(nama_akun), '') AS toko,
    NULLIF(TRIM(nama_produk), '') AS produk,
    CAST(NULL AS DECIMAL(18, 2)) AS harga,
    0 AS punya_harga,
    COALESCE(NULLIF(TRIM(lokasi), ''), 'Tidak diketahui') AS lokasi,
    COALESCE(NULLIF(TRIM(Kategori), ''), 'Tidak diketahui') AS kategori,
    NULL AS url
FROM ecommerce_valid
"""

ALL_ECOMMERCE_OVERVIEW_QUERY = f"""
SELECT
    COUNT(*) AS total_produk,
    COUNT(DISTINCT CONCAT(marketplace, ':', NULLIF(TRIM(toko), ''))) AS total_toko,
    COUNT(DISTINCT kategori) AS total_kategori,
    COUNT(DISTINCT lokasi) AS total_lokasi,
    ROUND(AVG(NULLIF(harga, 0)), 2) AS rata_rata_harga,
    MIN(NULLIF(harga, 0)) AS harga_min,
    MAX(NULLIF(harga, 0)) AS harga_max
FROM ({ALL_ECOMMERCE_UNION_QUERY}) all_ecommerce
"""

ALL_ECOMMERCE_MARKETPLACE_QUERY = f"""
SELECT
    marketplace,
    COUNT(*) AS total_produk,
    COUNT(DISTINCT NULLIF(TRIM(toko), '')) AS total_toko,
    COUNT(DISTINCT kategori) AS total_kategori,
    COUNT(DISTINCT lokasi) AS total_lokasi,
    ROUND(AVG(NULLIF(harga, 0)), 2) AS rata_rata_harga,
    MIN(NULLIF(harga, 0)) AS harga_min,
    MAX(NULLIF(harga, 0)) AS harga_max
FROM ({ALL_ECOMMERCE_UNION_QUERY}) all_ecommerce
GROUP BY marketplace
ORDER BY total_produk DESC, marketplace ASC
"""

ALL_ECOMMERCE_CATEGORY_QUERY = f"""
SELECT
    kategori,
    COUNT(*) AS jumlah,
    COUNT(DISTINCT marketplace) AS jumlah_marketplace
FROM ({ALL_ECOMMERCE_UNION_QUERY}) all_ecommerce
GROUP BY kategori
ORDER BY jumlah DESC, kategori ASC
LIMIT 12
"""

ALL_ECOMMERCE_STORE_CATEGORY_QUERY = f"""
SELECT
    kategori,
    COUNT(DISTINCT CONCAT(marketplace, ':', NULLIF(TRIM(toko), ''))) AS jumlah_toko,
    COUNT(*) AS jumlah_produk,
    COUNT(DISTINCT marketplace) AS jumlah_marketplace
FROM ({ALL_ECOMMERCE_UNION_QUERY}) all_ecommerce
GROUP BY kategori
ORDER BY jumlah_toko DESC, jumlah_produk DESC, kategori ASC
LIMIT 12
"""

ALL_ECOMMERCE_LOCATION_QUERY = f"""
SELECT
    lokasi,
    marketplace,
    COUNT(*) AS jumlah
FROM ({ALL_ECOMMERCE_UNION_QUERY}) all_ecommerce
GROUP BY lokasi, marketplace
ORDER BY jumlah DESC, lokasi ASC, marketplace ASC
"""

ALL_ECOMMERCE_STORE_LOCATION_QUERY = f"""
SELECT
    lokasi,
    marketplace,
    COUNT(DISTINCT NULLIF(TRIM(toko), '')) AS jumlah_toko,
    COUNT(*) AS jumlah_produk
FROM ({ALL_ECOMMERCE_UNION_QUERY}) all_ecommerce
GROUP BY lokasi, marketplace
ORDER BY jumlah_toko DESC, jumlah_produk DESC, lokasi ASC, marketplace ASC
"""

ALL_ECOMMERCE_PRICE_QUERY = f"""
SELECT
    rentang_harga,
    COUNT(*) AS jumlah
FROM (
    SELECT
        CASE
            WHEN harga IS NULL OR harga <= 0 THEN 'Tidak diketahui'
            WHEN harga < 50000 THEN '< Rp50 rb'
            WHEN harga < 100000 THEN 'Rp50 rb - Rp99 rb'
            WHEN harga < 250000 THEN 'Rp100 rb - Rp249 rb'
            WHEN harga < 500000 THEN 'Rp250 rb - Rp499 rb'
            WHEN harga < 1000000 THEN 'Rp500 rb - Rp999 rb'
            WHEN harga < 2500000 THEN 'Rp1 jt - Rp2,4 jt'
            WHEN harga < 5000000 THEN 'Rp2,5 jt - Rp4,9 jt'
            WHEN harga < 10000000 THEN 'Rp5 jt - Rp9,9 jt'
            WHEN harga < 25000000 THEN 'Rp10 jt - Rp24,9 jt'
            WHEN harga < 50000000 THEN 'Rp25 jt - Rp49,9 jt'
            ELSE '>= Rp50 jt'
        END AS rentang_harga,
        CASE
            WHEN harga IS NULL OR harga <= 0 THEN 0
            WHEN harga < 50000 THEN 1
            WHEN harga < 100000 THEN 2
            WHEN harga < 250000 THEN 3
            WHEN harga < 500000 THEN 4
            WHEN harga < 1000000 THEN 5
            WHEN harga < 2500000 THEN 6
            WHEN harga < 5000000 THEN 7
            WHEN harga < 10000000 THEN 8
            WHEN harga < 25000000 THEN 9
            WHEN harga < 50000000 THEN 10
            ELSE 11
        END AS urutan
    FROM ({ALL_ECOMMERCE_UNION_QUERY}) all_ecommerce
    WHERE punya_harga = 1
) distribusi_harga
GROUP BY rentang_harga, urutan
ORDER BY urutan
"""

ALL_ECOMMERCE_QUALITY_QUERY = f"""
SELECT
    marketplace,
    COUNT(*) AS total_produk,
    SUM(CASE WHEN toko IS NULL OR TRIM(toko) = '' THEN 1 ELSE 0 END) AS toko_kosong,
    SUM(CASE WHEN produk IS NULL OR TRIM(produk) = '' THEN 1 ELSE 0 END) AS produk_kosong,
    SUM(CASE WHEN lokasi = 'Tidak diketahui' THEN 1 ELSE 0 END) AS lokasi_tidak_diketahui,
    SUM(CASE WHEN kategori = 'Tidak diketahui' THEN 1 ELSE 0 END) AS kategori_tidak_diketahui,
    SUM(CASE WHEN punya_harga = 1 AND (harga IS NULL OR harga <= 0) THEN 1 ELSE 0 END) AS harga_tidak_valid
FROM ({ALL_ECOMMERCE_UNION_QUERY}) all_ecommerce
GROUP BY marketplace
ORDER BY marketplace ASC
"""

FACEBOOK_MARKETPLACE_OVERVIEW_QUERY = """
SELECT
    COUNT(*) AS total_data,
    COUNT(DISTINCT NULLIF(TRIM(nama_akun), '')) AS total_akun,
    COUNT(DISTINCT COALESCE(NULLIF(TRIM(lokasi), ''), 'Tidak diketahui')) AS total_lokasi,
    COUNT(DISTINCT COALESCE(NULLIF(TRIM(Kategori), ''), 'Tidak diketahui')) AS total_kategori,
    SUM(CASE WHEN LOWER(COALESCE(status_pedagang, '')) = 'pedagang' THEN 1 ELSE 0 END) AS total_pedagang,
    SUM(CASE WHEN LOWER(COALESCE(status_pedagang, '')) <> 'pedagang' THEN 1 ELSE 0 END) AS total_non_pedagang
FROM ecommerce_valid
"""

FACEBOOK_MARKETPLACE_PALU_OVERVIEW_QUERY = """
SELECT
    COUNT(*) AS total_data,
    COUNT(DISTINCT NULLIF(TRIM(nama_akun), '')) AS total_akun,
    COUNT(DISTINCT COALESCE(NULLIF(TRIM(Kategori), ''), 'Tidak diketahui')) AS total_kategori,
    SUM(CASE WHEN LOWER(COALESCE(status_pedagang, '')) = 'pedagang' THEN 1 ELSE 0 END) AS total_pedagang,
    SUM(CASE WHEN LOWER(COALESCE(status_pedagang, '')) <> 'pedagang' THEN 1 ELSE 0 END) AS total_non_pedagang
FROM ecommerce_valid
WHERE LOWER(COALESCE(lokasi, '')) LIKE '%palu%'
"""

FACEBOOK_MARKETPLACE_STATUS_QUERY = """
SELECT
    CASE
        WHEN LOWER(COALESCE(status_pedagang, '')) = 'pedagang' THEN 'Pedagang'
        ELSE 'Bukan pedagang'
    END AS status,
    COUNT(*) AS jumlah
FROM ecommerce_valid
GROUP BY
    CASE
        WHEN LOWER(COALESCE(status_pedagang, '')) = 'pedagang' THEN 'Pedagang'
        ELSE 'Bukan pedagang'
    END
ORDER BY jumlah DESC
"""

FACEBOOK_MARKETPLACE_PALU_STATUS_QUERY = """
SELECT
    CASE
        WHEN LOWER(COALESCE(status_pedagang, '')) = 'pedagang' THEN 'Pedagang'
        ELSE 'Bukan pedagang'
    END AS status,
    COUNT(*) AS jumlah
FROM ecommerce_valid
WHERE LOWER(COALESCE(lokasi, '')) LIKE '%palu%'
GROUP BY
    CASE
        WHEN LOWER(COALESCE(status_pedagang, '')) = 'pedagang' THEN 'Pedagang'
        ELSE 'Bukan pedagang'
    END
ORDER BY jumlah DESC
"""

FACEBOOK_MARKETPLACE_CATEGORY_QUERY = """
SELECT
    COALESCE(NULLIF(TRIM(Kategori), ''), 'Tidak diketahui') AS kategori,
    COUNT(*) AS jumlah
FROM ecommerce_valid
GROUP BY COALESCE(NULLIF(TRIM(Kategori), ''), 'Tidak diketahui')
ORDER BY jumlah DESC, kategori ASC
LIMIT 10
"""


def build_facebook_summary():
    community_data = build_community_dataset()
    community_overview = community_data["overview_rows"]
    community_groups = community_data["group_rows"]
    community_activity = community_data["intensity_rows"]

    community_total_accounts = sum(int(row.get("jumlah") or 0) for row in community_overview)
    community_seller_accounts = sum(
        int(row.get("jumlah") or 0)
        for row in community_overview
        if community_sort_text(row.get("kategori_final")) == "pedagang"
    )
    community_non_seller_accounts = community_total_accounts - community_seller_accounts
    community_total_posts = sum(int(row.get("jumlah_post") or 0) for row in community_activity)

    return {
        "marketplace": {
            "overview": query_view(FACEBOOK_MARKETPLACE_OVERVIEW_QUERY),
            "palu_overview": query_view(FACEBOOK_MARKETPLACE_PALU_OVERVIEW_QUERY),
            "status": query_view(FACEBOOK_MARKETPLACE_STATUS_QUERY),
            "palu_status": query_view(FACEBOOK_MARKETPLACE_PALU_STATUS_QUERY),
            "kategori": query_view(FACEBOOK_MARKETPLACE_CATEGORY_QUERY),
        },
        "community": {
            "scope": "Kota Palu",
            "overview": community_overview,
            "groups": community_groups[:10],
            "activity": community_activity[:10],
            "summary": {
                "total_akun": community_total_accounts,
                "total_pedagang": community_seller_accounts,
                "total_non_pedagang": community_non_seller_accounts,
                "total_post": community_total_posts,
                "total_grup": len(community_groups),
            },
        },
    }


# ===============================
# HALAMAN (FRONTEND)
# ===============================
def dashboard_page(request):
    return render(request, "dashboard.html")


def facebook_page(request):
    return render_protected_page(request, "facebook", "facebook.html")


def ecommerce_page(request):
    return render_protected_page(request, "ecommerce", "marketplace.html")


def tokopedia_page(request):
    return render_protected_page(request, "tokopedia", "tokopedia.html")


def shopee_page(request):
    return render_protected_page(request, "shopee", "shopee.html")


def lazada_page(request):
    return render_protected_page(request, "lazada", "lazada.html")


def blibli_page(request):
    return render_protected_page(request, "blibli", "blibli.html")


def get_grabfood_table_name():
    candidates = ("grabfood", "dashboard_grabfoodmerchant")
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
              AND table_name IN (%s, %s)
            """,
            candidates,
        )
        existing = {row[0] for row in cursor.fetchall()}

    for table_name in candidates:
        if table_name in existing:
            return table_name

    return candidates[0]


def normalize_grabfood_kab_kota(value):
    text = str(value or "").strip()
    return text or "Tidak Diketahui"


def normalize_grabfood_status(value):
    text = str(value or "").strip()
    return text or "Tidak Diketahui"


def is_grabfood_coordinate_valid(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "t", "yes", "y", "valid"}


def build_grabfood_context(request):
    table_name = get_grabfood_table_name()
    selected_kab_kota = request.GET.get("kab_kota", "").strip()
    selected_status = request.GET.get("status", "").strip()

    filters = []
    params = []

    if selected_kab_kota:
        if selected_kab_kota == "Tidak Diketahui":
            filters.append("(kab_kota IS NULL OR TRIM(kab_kota) = '')")
        else:
            filters.append("COALESCE(NULLIF(TRIM(kab_kota), ''), 'Tidak Diketahui') = %s")
            params.append(selected_kab_kota)

    if selected_status:
        if selected_status == "Tidak Diketahui":
            filters.append("(status_label IS NULL OR TRIM(status_label) = '')")
        else:
            filters.append("COALESCE(NULLIF(TRIM(status_label), ''), 'Tidak Diketahui') = %s")
            params.append(selected_status)

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    rows = query_view(
        f"""
        SELECT
            merchant_id,
            merchant_name,
            latitude,
            longitude,
            open_status,
            status_label,
            kab_kota,
            is_coordinate_valid
        FROM `{table_name}`
        {where_clause}
        ORDER BY merchant_name ASC, merchant_id ASC
        """,
        params,
    )

    merchants_by_id = {}
    for index, row in enumerate(rows):
        merchant_id = str(row.get("merchant_id") or "").strip() or f"row-{index + 1}"
        if merchant_id in merchants_by_id:
            continue

        merchants_by_id[merchant_id] = {
            "merchant_id": str(row.get("merchant_id") or "").strip(),
            "merchant_name": str(row.get("merchant_name") or "").strip() or "Tanpa Nama",
            "latitude": row.get("latitude"),
            "longitude": row.get("longitude"),
            "open_status": row.get("open_status"),
            "status_label": normalize_grabfood_status(row.get("status_label")),
            "kab_kota": normalize_grabfood_kab_kota(row.get("kab_kota")),
            "is_coordinate_valid": is_grabfood_coordinate_valid(row.get("is_coordinate_valid")),
        }

    merchant_rows = list(merchants_by_id.values())
    valid_location_rows = [
        row for row in merchant_rows
        if row["is_coordinate_valid"] and row.get("latitude") is not None and row.get("longitude") is not None
    ]

    kab_counts = {}
    status_counts = {}
    for row in merchant_rows:
        kab_counts[row["kab_kota"]] = kab_counts.get(row["kab_kota"], 0) + 1
        status_counts[row["status_label"]] = status_counts.get(row["status_label"], 0) + 1

    dominant_location = max(kab_counts.items(), key=lambda item: (item[1], item[0]))[0] if kab_counts else "Data belum tersedia"
    dominant_status = max(status_counts.items(), key=lambda item: (item[1], item[0]))[0] if status_counts else "Data belum tersedia"

    all_kab_kota = query_view(
        f"""
        SELECT DISTINCT COALESCE(NULLIF(TRIM(kab_kota), ''), 'Tidak Diketahui') AS value
        FROM `{table_name}`
        ORDER BY value ASC
        """
    )
    all_status = query_view(
        f"""
        SELECT DISTINCT COALESCE(NULLIF(TRIM(status_label), ''), 'Tidak Diketahui') AS value
        FROM `{table_name}`
        ORDER BY value ASC
        """
    )

    return {
        "grabfood_rows": json.dumps(merchant_rows, default=str),
        "grabfood_map_rows": json.dumps(valid_location_rows, default=str),
        "kab_kota_options": [row["value"] for row in all_kab_kota],
        "status_options": [row["value"] for row in all_status],
        "selected_kab_kota": selected_kab_kota,
        "selected_status": selected_status,
        "kpi": {
            "total_merchant": len(merchant_rows),
            "total_valid": len(valid_location_rows),
            "merchant_buka": sum(1 for row in merchant_rows if row["status_label"] == "Buka"),
            "merchant_tutup_sementara": sum(1 for row in merchant_rows if row["status_label"] != "Buka"),
            "kab_kota_terdata": len(kab_counts),
            "lokasi_dominan": dominant_location,
        },
        "insights": {
            "wilayah_dominan": dominant_location,
            "status_dominan": dominant_status,
            "cakupan_titik": len(valid_location_rows),
            "cakupan_wilayah": len(kab_counts),
        },
        "has_data": bool(merchant_rows),
    }


def build_grabfood_summary():
    table_name = get_grabfood_table_name()
    rows = query_view(
        f"""
        SELECT
            merchant_id,
            merchant_name,
            latitude,
            longitude,
            status_label,
            kab_kota,
            is_coordinate_valid
        FROM `{table_name}`
        ORDER BY merchant_name ASC, merchant_id ASC
        """
    )

    merchants_by_id = {}
    for index, row in enumerate(rows):
        merchant_id = str(row.get("merchant_id") or "").strip() or f"row-{index + 1}"
        if merchant_id in merchants_by_id:
            continue

        merchants_by_id[merchant_id] = {
            "merchant_id": str(row.get("merchant_id") or "").strip(),
            "merchant_name": str(row.get("merchant_name") or "").strip() or "Tanpa Nama",
            "latitude": row.get("latitude"),
            "longitude": row.get("longitude"),
            "status_label": normalize_grabfood_status(row.get("status_label")),
            "kab_kota": normalize_grabfood_kab_kota(row.get("kab_kota")),
            "is_coordinate_valid": is_grabfood_coordinate_valid(row.get("is_coordinate_valid")),
        }

    merchant_rows = list(merchants_by_id.values())
    kab_counts = {}
    status_counts = {}
    map_rows = []

    for row in merchant_rows:
        kab_counts[row["kab_kota"]] = kab_counts.get(row["kab_kota"], 0) + 1
        status_counts[row["status_label"]] = status_counts.get(row["status_label"], 0) + 1
        if row["is_coordinate_valid"] and row.get("latitude") is not None and row.get("longitude") is not None:
            map_rows.append({
                "merchant_name": row["merchant_name"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "kab_kota": row["kab_kota"],
                "status_label": row["status_label"],
            })

    dominant_location = max(kab_counts.items(), key=lambda item: (item[1], item[0]))[0] if kab_counts else "Data belum tersedia"

    per_kab_kota = [
        {"kab_kota": kab_kota, "jumlah": jumlah}
        for kab_kota, jumlah in sorted(kab_counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    status_summary = [
        {"status_label": status_label, "jumlah": jumlah}
        for status_label, jumlah in sorted(status_counts.items(), key=lambda item: (-item[1], item[0]))
    ]

    return {
        "summary": {
            "total_grabfood_merchant": len(merchant_rows),
            "grabfood_merchant_buka": sum(1 for row in merchant_rows if row["status_label"] == "Buka"),
            "grabfood_kab_kota_terdata": len(kab_counts),
            "grabfood_lokasi_dominan": dominant_location,
        },
        "map_data": map_rows,
        "per_kab_kota": per_kab_kota,
        "status_summary": status_summary,
    }


def grabfood_page(request):
    if not has_detail_access(request):
        return privacy_notice_page(request, RESTRICTED_SECTIONS["grabfood"])

    return render(request, "grabfood.html", build_grabfood_context(request))


def komunitas_page(request):
    return render_protected_page(request, "komunitas", "komunitas.html")


# ===============================
# DASHBOARD UTAMA (OVERVIEW)
# ===============================
def dashboard_overview(request):
    community_data = build_community_dataset()

    data = {
        # KPI Ecommerce
        "ecommerce_overview": query_view(
            "SELECT * FROM overview_ecommerce"
        ),

        # KPI Komunitas
        "komunitas_overview": community_data["overview_rows"],

        # Chart Ecommerce
        "ecommerce_pedagang": query_view(
            "SELECT * FROM pedagang_vs_non"
        ),

        # Chart Komunitas
        "komunitas_pedagang": community_data["overview_rows"],

        # Comparison: Ecommerce Kota Palu vs Komunitas Palu
        "ecommerce_palu_overview": query_view(
            """
            SELECT *
            FROM v_lokasi_pedagang
            WHERE LOWER(lokasi) LIKE '%palu%'
            """
        ),
    }

    return JsonResponse(data)


# ===============================
# ECOMMERCE API
# ===============================
def ecommerce_dashboard(request):
    restricted_response = require_detail_access(request, "Ecommerce detail")
    if restricted_response:
        return restricted_response

    return JsonResponse(build_ecommerce_summary_response(request, include_full=True))


def ecommerce_overview(request):
    restricted_response = require_detail_access(request, "Ecommerce overview detail")
    if restricted_response:
        return restricted_response

    return JsonResponse(build_ecommerce_summary_response(request, include_full=False))


def ecommerce_pedagang(request):
    restricted_response = require_detail_access(request, "Ecommerce pedagang detail")
    if restricted_response:
        return restricted_response

    return JsonResponse(build_ecommerce_summary_response(request, include_full=True))


def ecommerce_kategori(request):
    restricted_response = require_detail_access(request, "Ecommerce kategori detail")
    if restricted_response:
        return restricted_response

    return JsonResponse(build_ecommerce_summary_response(request, include_full=True))


def ecommerce_lokasi(request):
    restricted_response = require_detail_access(request, "Ecommerce lokasi detail")
    if restricted_response:
        return restricted_response

    return JsonResponse(build_ecommerce_summary_response(request, include_full=True))


def ecommerce_tabel(request):
    restricted_response = require_detail_access(request, "Ecommerce tabel detail")
    if restricted_response:
        return restricted_response

    return JsonResponse(query_view(f"{ALL_ECOMMERCE_UNION_QUERY} LIMIT 1000"), safe=False)


def ecommerce_summary_dashboard(request):
    return JsonResponse(build_ecommerce_summary_response(request, include_full=True))


def ecommerce_summary_quick(request):
    return JsonResponse(build_ecommerce_summary_response(request, include_full=False))


def tokopedia_dashboard(request):
    restricted_response = require_detail_access(request, "Tokopedia detail")
    if restricted_response:
        return restricted_response

    return JsonResponse(
        {
            "overview": query_view(TOKOPEDIA_OVERVIEW_QUERY),
            "kategori": query_view(TOKOPEDIA_KATEGORI_QUERY),
            "harga": query_view(TOKOPEDIA_HARGA_QUERY),
            "produk_lokasi": query_view(TOKOPEDIA_PRODUK_LOKASI_QUERY),
            "toko_lokasi": query_view(TOKOPEDIA_TOKO_LOKASI_QUERY),
        }
    )


def tokopedia_tabel(request):
    restricted_response = require_detail_access(request, "Tokopedia tabel detail")
    if restricted_response:
        return restricted_response

    return JsonResponse(query_view(TOKOPEDIA_TABLE_QUERY), safe=False)


def shopee_tabel(request):
    restricted_response = require_detail_access(request, "Shopee tabel detail")
    if restricted_response:
        return restricted_response

    return JsonResponse(query_view(SHOPEE_TABLE_QUERY), safe=False)


def lazada_tabel(request):
    restricted_response = require_detail_access(request, "Lazada tabel detail")
    if restricted_response:
        return restricted_response

    return JsonResponse(query_view(LAZADA_TABLE_QUERY), safe=False)


def blibli_tabel(request):
    restricted_response = require_detail_access(request, "Blibli tabel detail")
    if restricted_response:
        return restricted_response

    return JsonResponse(query_view(BLIBLI_TABLE_QUERY), safe=False)


# ===============================
# KOMUNITAS API
# ===============================
def komunitas_master(request):
    restricted_response = require_detail_access(request, "Komunitas master detail")
    if restricted_response:
        return restricted_response

    return JsonResponse(build_community_dataset()["master_rows"], safe=False)


def komunitas_overview(request):
    restricted_response = require_detail_access(request, "Komunitas overview detail")
    if restricted_response:
        return restricted_response

    return JsonResponse(build_community_dataset()["overview_rows"], safe=False)


def komunitas_grup(request):
    restricted_response = require_detail_access(request, "Komunitas grup detail")
    if restricted_response:
        return restricted_response

    return JsonResponse(build_community_dataset()["group_rows"], safe=False)


def komunitas_intensitas(request):
    restricted_response = require_detail_access(request, "Komunitas intensitas detail")
    if restricted_response:
        return restricted_response

    return JsonResponse(build_community_dataset()["intensity_rows"], safe=False)


# ===============================
# DEBUG (OPTIONAL)
# ===============================
def debug_ecommerce(request):
    return restricted_api_response("Debug ecommerce")


def debug_database(request):
    config = connection.settings_dict
    table_names = ("tokopedia", "shopee", "lazada", "blibli", "ecommerce_valid")
    response = {
        "database": {
            "engine": config.get("ENGINE"),
            "host": config.get("HOST"),
            "port": config.get("PORT"),
            "name": config.get("NAME"),
            "user": config.get("USER"),
        },
        "ok": False,
        "counts": {},
    }

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            response["database"]["current"] = cursor.fetchone()[0]

            for table_name in table_names:
                cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                response["counts"][table_name] = cursor.fetchone()[0]

        response["ok"] = True
        return JsonResponse(response)
    except Exception as error:
        response["error"] = {
            "type": error.__class__.__name__,
            "message": str(error),
        }
        return JsonResponse(response, status=500)
