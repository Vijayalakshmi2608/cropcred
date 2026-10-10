import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


class ProductionStartupTests(unittest.TestCase):
    def test_wsgi_entrypoint_serves_seeded_core_data(self):
        from wsgi import app

        client = app.test_client()
        self.assertEqual(client.get('/api/health').status_code, 200)
        for path in ('/api/harvests', '/api/crop-batches', '/api/marketplace', '/api/demands', '/api/auctions', '/api/orders'):
            response = client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertGreater(len(response.get_json()['data']), 0, path)


if __name__ == '__main__':
    unittest.main()
