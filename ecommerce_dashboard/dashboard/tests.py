from django.test import RequestFactory, SimpleTestCase

from . import views


class DashboardPageTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_dashboard_page_renders_ecommerce_summary(self):
        response = views.dashboard_page(self.factory.get('/'))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        self.assertIn('Dashboard Semua Ecommerce', content)
        self.assertIn('Facebook Marketplace', content)
        self.assertIn('marketplaceShareChart', content)
        self.assertIn('storeShareChart', content)
        self.assertIn('Produk per Toko', content)
        self.assertIn('facebookPaluComparisonChart', content)
        self.assertIn('/api/ecommerce/summary/', content)

    def test_tokopedia_page_renders_non_empty_dashboard(self):
        response = views.tokopedia_page(self.factory.get('/tokopedia/'))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        self.assertIn('Dashboard Tokopedia', content)
        self.assertIn('tokopediaTableBody', content)

    def test_shopee_page_renders_non_empty_dashboard(self):
        response = views.shopee_page(self.factory.get('/shopee/'))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        self.assertIn('Dashboard Shopee', content)
        self.assertIn('shopeeTableBody', content)

    def test_lazada_page_renders_non_empty_dashboard(self):
        response = views.lazada_page(self.factory.get('/lazada/'))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        self.assertIn('Dashboard Lazada', content)
        self.assertIn('lazadaTableBody', content)
