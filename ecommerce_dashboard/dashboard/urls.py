from django.urls import path
from . import views

urlpatterns = [

    # =====================
    # HALAMAN
    # =====================
    path('', views.dashboard_page, name='dashboard'),
    path('restricted/', views.privacy_notice_page, name='restricted'),
    path('facebook/', views.facebook_page, name='facebook'),
    path('ecommerce/', views.ecommerce_page, name='ecommerce'),
    path('tokopedia/', views.tokopedia_page, name='tokopedia'),
    path('shopee/', views.shopee_page, name='shopee'),
    path('lazada/', views.lazada_page, name='lazada'),
    path('blibli/', views.blibli_page, name='blibli'),
    path('grabfood/', views.grabfood_page, name='grabfood'),
    path('komunitas/', views.komunitas_page, name='komunitas'),

    # =====================
    # API DASHBOARD
    # =====================
    path('api/dashboard/', views.dashboard_overview),

    # =====================
    # ECOMMERCE
    # =====================
    path('api/ecommerce/dashboard/', views.ecommerce_dashboard),
    path('api/ecommerce/overview/', views.ecommerce_overview),
    path('api/ecommerce/pedagang/', views.ecommerce_pedagang),
    path('api/ecommerce/kategori/', views.ecommerce_kategori),
    path('api/ecommerce/lokasi/', views.ecommerce_lokasi),
    path('api/ecommerce/tabel/', views.ecommerce_tabel),
    path('api/ecommerce/summary/', views.ecommerce_summary_dashboard),
    path('api/ecommerce/summary/quick/', views.ecommerce_summary_quick),

    # =====================
    # TOKOPEDIA
    # =====================
    path('api/tokopedia/dashboard/', views.tokopedia_dashboard),
    path('api/tokopedia/tabel/', views.tokopedia_tabel),

    # =====================
    # SHOPEE
    # =====================
    path('api/shopee/tabel/', views.shopee_tabel),

    # =====================
    # LAZADA
    # =====================
    path('api/lazada/tabel/', views.lazada_tabel),

    # =====================
    # BLIBLI
    # =====================
    path('api/blibli/tabel/', views.blibli_tabel),

    # =====================
    # KOMUNITAS
    # =====================
    path('api/komunitas/master/', views.komunitas_master),
    path('api/komunitas/overview/', views.komunitas_overview),
    path('api/komunitas/grup/', views.komunitas_grup),
    path('api/komunitas/intensitas/', views.komunitas_intensitas),

    # =====================
    # DEBUG
    # =====================
    path('api/debug/ecommerce/', views.debug_ecommerce),
    path('api/debug/database/', views.debug_database),
]
