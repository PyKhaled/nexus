import os
import unittest
from http import HTTPStatus
from unittest.mock import patch

from project.app import response_for


class ResponseTests(unittest.TestCase):
    def test_health(self) -> None:
        status, payload = response_for("/healthz")
        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(payload, {"status": "ok"})

    def test_readiness(self) -> None:
        status, payload = response_for("/readyz")
        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(payload, {"status": "ready"})

    def test_root_uses_configuration(self) -> None:
        with patch.dict(
            os.environ,
            {"SERVICE_NAME": "example", "ENVIRONMENT": "test"},
            clear=False,
        ):
            status, payload = response_for("/")

        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(payload["service"], "example")
        self.assertEqual(payload["environment"], "test")

    def test_unknown_path(self) -> None:
        status, payload = response_for("/missing")
        self.assertEqual(status, HTTPStatus.NOT_FOUND)
        self.assertEqual(payload, {"error": "not_found"})


if __name__ == "__main__":
    unittest.main()
