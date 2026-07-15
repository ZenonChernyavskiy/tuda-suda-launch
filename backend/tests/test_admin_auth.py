import os
import unittest


os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key-123456789012345678")
os.environ.setdefault(
    "HOT_WALLET_ADDRESS",
    "UQCaKtJZrSwLgcYwGYSG9Qijyn73oRdXIinxx-zBQ752TXxo",
)

from fastapi import HTTPException  # noqa: E402
from app.main import require_admin  # noqa: E402


class AdminAuthTestCase(unittest.TestCase):
    def test_admin_token_is_required(self) -> None:
        with self.assertRaises(HTTPException) as context:
            require_admin(None)
        self.assertEqual(context.exception.status_code, 403)

    def test_invalid_admin_token_is_rejected(self) -> None:
        with self.assertRaises(HTTPException) as context:
            require_admin("wrong-token")
        self.assertEqual(context.exception.status_code, 403)

    def test_valid_admin_token_is_accepted(self) -> None:
        self.assertIsNone(
            require_admin("test-admin-key-123456789012345678")
        )
