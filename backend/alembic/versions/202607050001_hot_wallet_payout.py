"""hot wallet payout fields

Revision ID: 202607050001
Revises: 202607010001
Create Date: 2026-07-05
"""

from alembic import op
import sqlalchemy as sa


revision = "202607050001"
down_revision = "202607010001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("asset_deposits")}
    indexes = {index["name"] for index in inspector.get_indexes("asset_deposits")}

    if "payout_status" not in columns:
        op.add_column(
            "asset_deposits",
            sa.Column(
                "payout_status",
                sa.String(length=32),
                nullable=False,
                server_default="pending",
            ),
        )
    if "payout_tx_hash" not in columns:
        op.add_column(
            "asset_deposits",
            sa.Column("payout_tx_hash", sa.String(length=128), nullable=True),
        )
    if "payout_failed_reason" not in columns:
        op.add_column(
            "asset_deposits",
            sa.Column("payout_failed_reason", sa.String(length=500), nullable=True),
        )
    if "payout_sent_at" not in columns:
        op.add_column(
            "asset_deposits",
            sa.Column("payout_sent_at", sa.DateTime(), nullable=True),
        )
    if "payout_confirmed_at" not in columns:
        op.add_column(
            "asset_deposits",
            sa.Column("payout_confirmed_at", sa.DateTime(), nullable=True),
        )

    bind.execute(
        sa.text(
            "UPDATE asset_deposits "
            "SET payout_status = 'pending' "
            "WHERE payout_status IS NULL OR payout_status = ''"
        )
    )

    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("asset_deposits")}
    if "ix_asset_deposits_payout_status" not in indexes:
        op.create_index(
            "ix_asset_deposits_payout_status",
            "asset_deposits",
            ["payout_status"],
        )
    if "ix_asset_deposits_payout_tx_hash" not in indexes:
        op.create_index(
            "ix_asset_deposits_payout_tx_hash",
            "asset_deposits",
            ["payout_tx_hash"],
            unique=True,
        )


def downgrade() -> None:
    op.drop_index("ix_asset_deposits_payout_tx_hash", table_name="asset_deposits")
    op.drop_index("ix_asset_deposits_payout_status", table_name="asset_deposits")
    op.drop_column("asset_deposits", "payout_confirmed_at")
    op.drop_column("asset_deposits", "payout_sent_at")
    op.drop_column("asset_deposits", "payout_failed_reason")
    op.drop_column("asset_deposits", "payout_tx_hash")
    op.drop_column("asset_deposits", "payout_status")
