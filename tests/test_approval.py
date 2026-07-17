from __future__ import annotations

import unittest
from unittest.mock import patch

from scandroid import approval


REQUEST_ID = "12345678-1234-4234-9234-123456789abc"


class FakeResponse:
    def __init__(self, payload, *, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


class FakeRequests:
    def __init__(self, *, post_payload=None, get_payload=None):
        self.post_payload = post_payload
        self.get_payload = get_payload
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return FakeResponse(self.post_payload)

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return FakeResponse(self.get_payload)


class ApprovalClientTests(unittest.TestCase):
    def test_rejects_insecure_nonlocal_worker_url(self):
        with self.assertRaisesRegex(ValueError, "must use HTTPS"):
            approval._config("agent-token", "http://approval.example.com")

    def test_allows_http_for_local_development(self):
        self.assertEqual(
            approval._config("agent-token", "http://127.0.0.1:8787/"),
            ("http://127.0.0.1:8787", "agent-token"),
        )

    def test_request_validates_ttl_before_network(self):
        with self.assertRaisesRegex(ValueError, "ttl_seconds"):
            approval.request(
                "deploy",
                ttl_seconds=1,
                token="agent-token",
                url="https://approval.example.com",
            )

    def test_request_normalizes_action_and_validates_response(self):
        fake = FakeRequests(
            post_payload={
                "request_id": REQUEST_ID,
                "expires_at": 1234567890,
                "approve_url": "https://approval.example.com/ui?id=x",
            }
        )
        with patch.object(approval, "_requests", return_value=fake):
            result = approval.request(
                "  deploy.preview  ",
                details={"target": "ghost"},
                ttl_seconds=60,
                token="agent-token",
                url="https://approval.example.com",
            )
        self.assertEqual(result["request_id"], REQUEST_ID)
        method, _, kwargs = fake.calls[0]
        self.assertEqual(method, "POST")
        self.assertEqual(kwargs["json"]["action"], "deploy.preview")
        self.assertEqual(kwargs["json"]["ttl_seconds"], 60)
        self.assertEqual(kwargs["headers"]["Accept"], "application/json")

    def test_status_rejects_mismatched_record(self):
        fake = FakeRequests(
            get_payload={
                "request_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                "status": "pending",
            }
        )
        with patch.object(approval, "_requests", return_value=fake):
            with self.assertRaisesRegex(RuntimeError, "mismatched request_id"):
                approval.status(
                    REQUEST_ID,
                    token="agent-token",
                    url="https://approval.example.com",
                )

    def test_wait_returns_terminal_record_without_sleeping(self):
        terminal = {"request_id": REQUEST_ID, "status": "approved"}
        with patch.object(approval, "status", return_value=terminal) as status_call:
            result = approval.wait(
                REQUEST_ID,
                timeout=1,
                poll_interval=0.01,
                token="agent-token",
                url="https://approval.example.com",
            )
        self.assertEqual(result, terminal)
        status_call.assert_called_once()

    def test_cancel_normalizes_request_id(self):
        fake = FakeRequests(post_payload={"ok": True, "request_id": REQUEST_ID})
        with patch.object(approval, "_requests", return_value=fake):
            result = approval.cancel(
                REQUEST_ID.upper(),
                token="agent-token",
                url="https://approval.example.com",
            )
        self.assertTrue(result["ok"])
        self.assertEqual(fake.calls[0][2]["json"]["request_id"], REQUEST_ID)


if __name__ == "__main__":
    unittest.main()
