"""Integration test: run against the local server on port 8000."""
import json
import unittest
from urllib.request import urlopen


class HealthEndpointTest(unittest.TestCase):
    def test_health(self):
        with urlopen("http://127.0.0.1:8000/health", timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(json.load(response), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
