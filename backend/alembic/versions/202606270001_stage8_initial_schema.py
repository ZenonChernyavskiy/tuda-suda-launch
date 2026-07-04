"""stage8 initial production schema

Revision ID: 202606270001
Revises:
Create Date: 2026-06-27
"""

from alembic import op
import sqlalchemy as sa


revision = "202606270001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.String(length=64), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("first_name", sa.String(length=128), nullable=True),
        sa.Column("photo_url", sa.String(length=512), nullable=True),
        sa.Column("balance", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("karma", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reputation", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("risk_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("community_weight", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ton_balance", sa.Numeric(18, 9), nullable=False, server_default="0"),
        sa.Column("ton_balance_nano", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("ton_wallet_address", sa.String(length=128), nullable=True),
        sa.Column("ton_wallet_connected_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("last_active_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("telegram_id"),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"])
    op.create_index("ix_users_reputation", "users", ["reputation"])
    op.create_index("ix_users_risk_score", "users", ["risk_score"])
    op.create_index("ix_users_community_weight", "users", ["community_weight"])

    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("asset_type", sa.String(length=32), nullable=False),
        sa.Column("network", sa.String(length=32), nullable=False),
        sa.Column("decimals", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("contract_address", sa.String(length=128), nullable=True),
        sa.Column("provider_key", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("symbol"),
    )
    op.create_index("ix_assets_id", "assets", ["id"])
    op.create_index("ix_assets_symbol", "assets", ["symbol"])
    op.create_index("ix_assets_asset_type", "assets", ["asset_type"])
    op.create_index("ix_assets_network", "assets", ["network"])
    op.create_index("ix_assets_provider_key", "assets", ["provider_key"])
    op.create_index("ix_assets_display_order", "assets", ["display_order"])
    op.create_index("ix_assets_is_active", "assets", ["is_active"])

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sender_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("receiver_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_transactions_id", "transactions", ["id"])
    op.create_index("ix_transactions_sender_id", "transactions", ["sender_id"])
    op.create_index("ix_transactions_receiver_id", "transactions", ["receiver_id"])
    op.create_index("ix_transactions_created_at", "transactions", ["created_at"])

    op.create_table(
        "wallet_connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("network", sa.String(length=32), nullable=False, server_default="ton"),
        sa.Column("wallet_address", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("connected_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("disconnected_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_wallet_connections_id", "wallet_connections", ["id"])
    op.create_index("ix_wallet_connections_user_id", "wallet_connections", ["user_id"])
    op.create_index("ix_wallet_connections_network", "wallet_connections", ["network"])
    op.create_index("ix_wallet_connections_wallet_address", "wallet_connections", ["wallet_address"])
    op.create_index("ix_wallet_connections_is_active", "wallet_connections", ["is_active"])

    op.create_table(
        "reputation_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("karma_delta", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reputation_delta", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("risk_delta", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("related_entity_type", sa.String(length=64), nullable=True),
        sa.Column("related_entity_id", sa.Integer(), nullable=True),
        sa.Column("comment", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_reputation_events_id", "reputation_events", ["id"])
    op.create_index("ix_reputation_events_user_id", "reputation_events", ["user_id"])
    op.create_index("ix_reputation_events_event_type", "reputation_events", ["event_type"])
    op.create_index("ix_reputation_events_created_at", "reputation_events", ["created_at"])

    op.create_table(
        "asset_balances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("balance_units", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "asset_id", name="uq_asset_balance_user_asset"),
    )
    op.create_index("ix_asset_balances_id", "asset_balances", ["id"])
    op.create_index("ix_asset_balances_user_id", "asset_balances", ["user_id"])
    op.create_index("ix_asset_balances_asset_id", "asset_balances", ["asset_id"])

    op.create_table(
        "asset_ledger_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("entry_type", sa.String(length=32), nullable=False),
        sa.Column("amount_units", sa.BigInteger(), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("related_entity_type", sa.String(length=64), nullable=True),
        sa.Column("related_entity_id", sa.Integer(), nullable=True),
        sa.Column("balance_after_units", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("comment", sa.String(length=500), nullable=True),
    )
    op.create_index("ix_asset_ledger_entries_id", "asset_ledger_entries", ["id"])
    op.create_index("ix_asset_ledger_entries_user_id", "asset_ledger_entries", ["user_id"])
    op.create_index("ix_asset_ledger_entries_asset_id", "asset_ledger_entries", ["asset_id"])
    op.create_index("ix_asset_ledger_entries_entry_type", "asset_ledger_entries", ["entry_type"])
    op.create_index("ix_asset_ledger_entries_direction", "asset_ledger_entries", ["direction"])
    op.create_index("ix_asset_ledger_entries_created_at", "asset_ledger_entries", ["created_at"])

    op.create_table(
        "asset_gifts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sender_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("receiver_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("amount_units", sa.BigInteger(), nullable=False),
        sa.Column("fee_units", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("net_amount_units", sa.BigInteger(), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="completed"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_asset_gifts_id", "asset_gifts", ["id"])
    op.create_index("ix_asset_gifts_sender_id", "asset_gifts", ["sender_id"])
    op.create_index("ix_asset_gifts_receiver_id", "asset_gifts", ["receiver_id"])
    op.create_index("ix_asset_gifts_asset_id", "asset_gifts", ["asset_id"])
    op.create_index("ix_asset_gifts_status", "asset_gifts", ["status"])
    op.create_index("ix_asset_gifts_created_at", "asset_gifts", ["created_at"])

    op.create_table(
        "asset_deposits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("wallet_address", sa.String(length=128), nullable=False),
        sa.Column("target_wallet_address", sa.String(length=128), nullable=False),
        sa.Column("amount_units", sa.BigInteger(), nullable=False),
        sa.Column("tx_hash", sa.String(length=128), nullable=True),
        sa.Column("comment", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("network", sa.String(length=32), nullable=False),
        sa.Column("failed_reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("tx_hash"),
        sa.UniqueConstraint("comment"),
    )
    op.create_index("ix_asset_deposits_id", "asset_deposits", ["id"])
    op.create_index("ix_asset_deposits_user_id", "asset_deposits", ["user_id"])
    op.create_index("ix_asset_deposits_asset_id", "asset_deposits", ["asset_id"])
    op.create_index("ix_asset_deposits_wallet_address", "asset_deposits", ["wallet_address"])
    op.create_index("ix_asset_deposits_target_wallet_address", "asset_deposits", ["target_wallet_address"])
    op.create_index("ix_asset_deposits_tx_hash", "asset_deposits", ["tx_hash"])
    op.create_index("ix_asset_deposits_comment", "asset_deposits", ["comment"])
    op.create_index("ix_asset_deposits_status", "asset_deposits", ["status"])
    op.create_index("ix_asset_deposits_provider", "asset_deposits", ["provider"])
    op.create_index("ix_asset_deposits_network", "asset_deposits", ["network"])
    op.create_index("ix_asset_deposits_created_at", "asset_deposits", ["created_at"])

    op.create_table(
        "ton_deposits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("wallet_address", sa.String(length=128), nullable=False),
        sa.Column("target_wallet_address", sa.String(length=128), nullable=True),
        sa.Column("network", sa.String(length=32), nullable=False, server_default="testnet"),
        sa.Column("amount_ton", sa.Numeric(18, 9), nullable=False),
        sa.Column("amount_nano", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("tx_hash", sa.String(length=128), nullable=True),
        sa.Column("comment", sa.String(length=160), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("failed_reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("tx_hash"),
    )
    op.create_index("ix_ton_deposits_id", "ton_deposits", ["id"])
    op.create_index("ix_ton_deposits_user_id", "ton_deposits", ["user_id"])
    op.create_index("ix_ton_deposits_wallet_address", "ton_deposits", ["wallet_address"])
    op.create_index("ix_ton_deposits_tx_hash", "ton_deposits", ["tx_hash"])
    op.create_index("ix_ton_deposits_created_at", "ton_deposits", ["created_at"])


def downgrade() -> None:
    op.drop_table("ton_deposits")
    op.drop_table("asset_deposits")
    op.drop_table("asset_gifts")
    op.drop_table("asset_ledger_entries")
    op.drop_table("asset_balances")
    op.drop_table("reputation_events")
    op.drop_table("wallet_connections")
    op.drop_table("transactions")
    op.drop_table("assets")
    op.drop_table("users")
