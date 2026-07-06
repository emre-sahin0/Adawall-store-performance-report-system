import unittest
from app import app


class KapatRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_kapat_logs_out_and_redirects_to_login(self):
        with self.client.session_transaction() as session:
            session['logged_in'] = True

        response = self.client.get('/kapat', follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], '/login')

        with self.client.session_transaction() as session:
            self.assertNotIn('logged_in', session)


if __name__ == '__main__':
    unittest.main()
