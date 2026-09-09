import base64
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from app.main import app


class RequestPolicyTests(unittest.TestCase):
    def test_hosted_password_and_health_probe(self):
        with patch.dict(os.environ,{'SCANPILOT_PASSWORD':'test-only-password'}):
            client=TestClient(app)
            self.assertEqual(client.get('/').status_code,401)
            self.assertEqual(client.get('/api/health').status_code,200)
            self.assertEqual(client.get('/',headers={'Authorization':'Basic !!!'}).status_code,401)
            token=base64.b64encode(b'scanpilot:test-only-password').decode()
            self.assertEqual(client.get('/',headers={'Authorization':'Basic '+token}).status_code,200)

    def test_total_request_limit(self):
        client=TestClient(app)
        response=client.post('/api/analyze',content=b'x',headers={'Content-Length':str(26*1024*1024)})
        self.assertEqual(response.status_code,413)


if __name__=='__main__':unittest.main()
