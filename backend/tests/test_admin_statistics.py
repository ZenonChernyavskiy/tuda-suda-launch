import os
import unittest
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite://")

from app import models  # noqa: E402
from app.admin_statistics import (  # noqa: E402
    build_admin_activity,
    build_admin_overview,
    build_admin_timeseries,
    build_admin_users_page,
)
from app.database import Base  # noqa: E402


TDSD = 1_000_000_000


class AdminStatisticsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.now = datetime(2026, 7, 15, 12, 0, 0)
        self._seed_data()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _seed_data(self) -> None:
        asset = models.Asset(
            symbol="TDSD",
            name="Tuda Suda Token",
            asset_type="jetton",
            network="ton_mainnet",
            decimals=9,
            provider_key="tdsd_fixed_price",
            is_active=True,
        )
        treasury = models.User(
            telegram_id="system:treasury",
            username="treasury",
            first_name="Treasury",
            created_at=self.now - timedelta(days=50),
        )
        sender = models.User(
            telegram_id="1001",
            username="sender",
            first_name="Sender",
            ton_wallet_address="wallet-1",
            ton_wallet_connected_at=self.now - timedelta(days=30),
            referral_code="SEND1001",
            karma=15,
            reputation=7,
            risk_score=1,
            community_weight=8,
            total_sent=3,
            total_received=2,
            created_at=self.now - timedelta(days=40),
            last_active_at=self.now - timedelta(hours=1),
        )
        receiver = models.User(
            telegram_id="1002",
            username="receiver",
            first_name="Receiver",
            created_at=self.now - timedelta(days=2),
            last_active_at=self.now - timedelta(days=2),
        )
        newcomer = models.User(
            telegram_id="1003",
            username=None,
            first_name="New User",
            created_at=self.now - timedelta(hours=1),
            last_active_at=self.now - timedelta(hours=1),
        )
        self.db.add_all([asset, treasury, sender, receiver, newcomer])
        self.db.flush()

        receiver.referred_by_user_id = sender.id
        receiver.referred_at = self.now - timedelta(days=2)

        self.db.add_all(
            [
                models.AssetBalance(
                    user_id=sender.id,
                    asset_id=asset.id,
                    balance_units=25 * TDSD,
                ),
                models.AssetGift(
                    sender_id=sender.id,
                    receiver_id=receiver.id,
                    asset_id=asset.id,
                    amount_units=100 * TDSD,
                    fee_units=10 * TDSD,
                    net_amount_units=90 * TDSD,
                    status="completed",
                    created_at=self.now - timedelta(days=1),
                ),
                models.AssetGift(
                    sender_id=sender.id,
                    receiver_id=newcomer.id,
                    asset_id=asset.id,
                    amount_units=20 * TDSD,
                    fee_units=2 * TDSD,
                    net_amount_units=18 * TDSD,
                    status="failed",
                    created_at=self.now - timedelta(hours=2),
                ),
            ]
        )

        successful = models.AssetDeposit(
            user_id=sender.id,
            asset_id=asset.id,
            wallet_address="wallet-1",
            target_wallet_address="hot-wallet",
            amount_units=100 * TDSD,
            comment="purchase-success",
            status="confirmed",
            provider="tdsd_fixed_price",
            network="ton_mainnet",
            payout_status="sent",
            created_at=self.now - timedelta(days=1),
            confirmed_at=self.now - timedelta(days=1),
        )
        payout_failed = models.AssetDeposit(
            user_id=receiver.id,
            asset_id=asset.id,
            wallet_address="wallet-2",
            target_wallet_address="hot-wallet",
            amount_units=50 * TDSD,
            comment="purchase-payout-failed",
            status="confirmed",
            provider="tdsd_fixed_price",
            network="ton_mainnet",
            payout_status="failed",
            payout_failed_reason="Payout failed",
            created_at=self.now - timedelta(hours=20),
            confirmed_at=self.now - timedelta(hours=20),
        )
        pending = models.AssetDeposit(
            user_id=newcomer.id,
            asset_id=asset.id,
            wallet_address="wallet-3",
            target_wallet_address="hot-wallet",
            amount_units=20 * TDSD,
            comment="purchase-pending",
            status="pending",
            provider="tdsd_fixed_price",
            network="ton_mainnet",
            payout_status="pending",
            created_at=self.now - timedelta(hours=2),
        )
        payment_failed = models.AssetDeposit(
            user_id=newcomer.id,
            asset_id=asset.id,
            wallet_address="wallet-3",
            target_wallet_address="hot-wallet",
            amount_units=10 * TDSD,
            comment="purchase-payment-failed",
            status="failed",
            provider="tdsd_fixed_price",
            network="ton_mainnet",
            payout_status="pending",
            failed_reason="Payment not found",
            created_at=self.now - timedelta(hours=1),
        )
        self.db.add_all([successful, payout_failed, pending, payment_failed])
        self.db.flush()

        self.db.add_all(
            [
                models.AssetLedgerEntry(
                    user_id=sender.id,
                    asset_id=asset.id,
                    entry_type="fee_purchase",
                    amount_units=1 * TDSD,
                    direction="debit",
                    related_entity_type="asset_deposit",
                    related_entity_id=successful.id,
                    balance_after_units=0,
                    created_at=self.now - timedelta(days=1),
                ),
                models.AssetLedgerEntry(
                    user_id=receiver.id,
                    asset_id=asset.id,
                    entry_type="fee_purchase",
                    amount_units=TDSD // 2,
                    direction="debit",
                    related_entity_type="asset_deposit",
                    related_entity_id=payout_failed.id,
                    balance_after_units=0,
                    created_at=self.now - timedelta(hours=20),
                ),
                models.UserReveal(
                    viewer_user_id=sender.id,
                    revealed_user_id=receiver.id,
                    context_type="asset_gift",
                    context_id="1",
                    target_role="receiver",
                    price_units=10 * TDSD,
                    created_at=self.now - timedelta(hours=3),
                ),
                models.ReferralReward(
                    referrer_user_id=sender.id,
                    referred_user_id=receiver.id,
                    purchase_id=successful.id,
                    purchase_amount_tdsd=100 * TDSD,
                    reward_amount_tdsd=5 * TDSD,
                    reward_percent=5,
                    status="credited",
                    created_at=self.now - timedelta(days=1),
                    credited_at=self.now - timedelta(days=1),
                ),
                models.Transaction(
                    sender_id=sender.id,
                    receiver_id=receiver.id,
                    amount=5,
                    created_at=self.now - timedelta(days=1),
                ),
            ]
        )
        self.db.commit()

    def test_overview_excludes_system_users_and_tracks_successful_operations(self) -> None:
        result = build_admin_overview(self.db, "7d", now=self.now)

        self.assertEqual(result.users.total, 3)
        self.assertEqual(result.users.new_in_period, 2)
        self.assertEqual(result.users.active_in_period, 3)
        self.assertEqual(result.users.active_1d, 2)
        self.assertEqual(result.users.wallets_connected, 1)

        self.assertEqual(result.gifts.count, 1)
        self.assertEqual(result.gifts.gross_display, "100")
        self.assertEqual(result.gifts.net_display, "90")
        self.assertEqual(result.gifts.fee_display, "10")
        self.assertEqual(result.gifts.unique_senders, 1)
        self.assertEqual(result.gifts.unique_receivers, 1)

        self.assertEqual(result.purchases.created, 4)
        self.assertEqual(result.purchases.pending_payment, 1)
        self.assertEqual(result.purchases.payment_confirmed, 2)
        self.assertEqual(result.purchases.successful, 1)
        self.assertEqual(result.purchases.payment_failed, 1)
        self.assertEqual(result.purchases.payout_failed, 1)
        self.assertEqual(result.purchases.purchased_display, "100")
        self.assertEqual(result.purchases.payment_amount_ton, "10")

        self.assertEqual(result.revenue.purchase_fee_display, "1.5")
        self.assertEqual(result.revenue.transfer_fee_display, "10")
        self.assertEqual(result.revenue.reveal_income_display, "10")
        self.assertEqual(result.revenue.total_display, "21.5")
        self.assertEqual(result.referrals.invited_users, 1)
        self.assertEqual(result.referrals.credited_reward_display, "5")
        self.assertEqual(result.legacy_transactions_count, 1)

    def test_timeseries_fills_empty_days_and_uses_successful_purchases_only(self) -> None:
        result = build_admin_timeseries(self.db, 3, now=self.now)

        self.assertEqual(len(result.points), 3)
        by_date = {point.date.isoformat(): point for point in result.points}
        self.assertEqual(by_date["2026-07-13"].new_users, 1)
        self.assertEqual(by_date["2026-07-14"].gifts_count, 1)
        self.assertEqual(by_date["2026-07-14"].purchases_count, 1)
        self.assertEqual(by_date["2026-07-14"].purchase_volume_display, "100")
        self.assertEqual(by_date["2026-07-15"].new_users, 1)
        self.assertEqual(by_date["2026-07-15"].purchases_count, 0)

    def test_activity_exposes_payout_failure_without_telegram_ids(self) -> None:
        result = build_admin_activity(self.db, 10)

        failed = next(
            row for row in result.recent_purchases if row.payout_status == "failed"
        )
        self.assertEqual(failed.user, "@receiver")
        self.assertEqual(failed.error, "Payout failed")
        self.assertNotIn("1002", failed.user)
        self.assertEqual(result.recent_gifts[0].sender, "@sender")

    def test_users_page_excludes_system_users_and_includes_saved_data(self) -> None:
        result = build_admin_users_page(
            self.db,
            limit=2,
            offset=0,
        )

        self.assertEqual(result.total, 3)
        self.assertEqual(len(result.items), 2)
        self.assertEqual(result.items[0].telegram_id, "1003")

        sender_page = build_admin_users_page(
            self.db,
            limit=10,
            offset=0,
            query="wallet-1",
        )
        self.assertEqual(sender_page.total, 1)
        sender = sender_page.items[0]
        self.assertEqual(sender.username, "sender")
        self.assertEqual(sender.tdsd_balance_display, "25")
        self.assertEqual(sender.referral_code, "SEND1001")
        self.assertEqual(sender.karma, 15)

    def test_users_page_supports_pagination_and_referrer_label(self) -> None:
        second_page = build_admin_users_page(
            self.db,
            limit=1,
            offset=1,
        )

        self.assertEqual(second_page.total, 3)
        self.assertEqual(len(second_page.items), 1)
        self.assertEqual(second_page.items[0].telegram_id, "1002")
        self.assertEqual(second_page.items[0].referrer, "@sender")


if __name__ == "__main__":
    unittest.main()
