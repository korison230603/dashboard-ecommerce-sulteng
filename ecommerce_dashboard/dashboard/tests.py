from django.test import RequestFactory, SimpleTestCase

from . import views


class DashboardPageTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_dashboard_page_renders_ecommerce_summary(self):
        response = views.dashboard_page(self.factory.get('/'))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        self.assertIn('Ringkasan Aktivitas Pelaku Usaha Digital Sulawesi Tengah', content)
        self.assertIn('Facebook Marketplace', content)
        self.assertIn('productPlatformChart', content)
        self.assertIn('accountPlatformChart', content)
        self.assertIn('Produk per Toko', content)
        self.assertIn('paluComparisonChart', content)
        self.assertIn('/api/ecommerce/summary/', content)

    def test_tokopedia_page_renders_non_empty_dashboard(self):
        response = views.tokopedia_page(self.factory.get('/tokopedia/'))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        self.assertIn('Akses Terbatas', content)
        self.assertIn('Tokopedia tidak ditampilkan untuk publik', content)
        self.assertNotIn('tokopediaTableBody', content)

    def test_shopee_page_renders_privacy_notice(self):
        response = views.shopee_page(self.factory.get('/shopee/'))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        self.assertIn('Akses Terbatas', content)
        self.assertIn('Shopee tidak ditampilkan untuk publik', content)
        self.assertNotIn('shopeeTableBody', content)

    def test_lazada_page_renders_privacy_notice(self):
        response = views.lazada_page(self.factory.get('/lazada/'))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        self.assertIn('Akses Terbatas', content)
        self.assertIn('Lazada tidak ditampilkan untuk publik', content)
        self.assertNotIn('lazadaTableBody', content)

    def test_detail_api_is_restricted(self):
        response = views.tokopedia_tabel(self.factory.get('/api/tokopedia/tabel/'))

        self.assertEqual(response.status_code, 403)
        content = response.content.decode()

        self.assertIn('restricted', content)
        self.assertIn('privasi data pelaku usaha', content)
