"""referral program

Revision ID: 202607010001
Revises: 202606270001
Create Date: 2026-07-01
"""

import hashlib

from alembic import op
import sqlalchemy as sa


revision = "202607010001"
down_revision = "202606270001"
branch_labels = None
depends_on = None


REFERRAL_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _referral_code(user_id: int, telegram_id: str | None) -> str:
    seed = f"{user_id}:{telegram_id or ''}:tuda-suda-referral".encode()
    number = int.from_bytes(hashlib.sha256(seed).digest()[:8], "big")
    chars = []
    for _ in range(8):
        number, index = divmod(number, len(REFERRAL_CODE_ALPHABET))
        chars.append(REFERRAL_CODE_ALPHABET[index])
    return "".join(chars)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    user_indexes = {index["name"] for index in inspector.get_indexes("users")}

    if "referral_code" not in user_columns:
        op.add_column("users", sa.Column("referral_code", sa.String(length=16), nullable=True))
    if "referred_by_user_id" not in user_columns:
        op.add_column("users", sa.Column("referred_by_user_id", sa.Integer(), nullable=True))
    if "referred_at" not in user_columns:
        op.add_column("users", sa.Column("referred_at", sa.DateTime(), nullable=True))

    existing_codes: set[str] = {
        row[0]
        for row in bind.execute(
            sa.text("SELECT referral_code FROM users WHERE referral_code IS NOT NULL")
        ).all()
        if row[0]
    }
    rows = bind.execute(
        sa.text(
            "SELECT id, telegram_id FROM users "
            "WHERE referral_code IS NULL OR referral_code = ''"
        )
    ).all()
    for row in rows:
        user_id, telegram_id = row[0], row[1]
        code = _referral_code(user_id, telegram_id)
        suffix = 1
        while code in existing_codes:
            code = _referral_code(user_id + suffix, telegram_id)
            suffix += 1
        existing_codes.add(code)
        bind.execute(
            sa.text("UPDATE users SET referral_code = :code WHERE id = :user_id"),
            {"code": code, "user_id": user_id},
        )

    if "ix_users_referral_code" not in user_indexes:
        op.create_index(
            "ix_users_referral_code",
            "users",
            ["referral_code"],
            unique=True,
        )
    if "ix_users_referred_by_user_id" not in user_indexes:
        op.create_index("ix_users_referred_by_user_id", "users", ["referred_by_user_id"])

    if "referral_rewards" not in inspector.get_table_names():
        op.create_table(
            "referral_rewards",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("referrer_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("referred_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("purchase_id", sa.Integer(), nullable=True),
            sa.Column("purchase_amount_tdsd", sa.BigInteger(), nullable=False),
            sa.Column("reward_amount_tdsd", sa.BigInteger(), nullable=False),
            sa.Column("reward_percent", sa.Numeric(8, 4), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("credited_at", sa.DateTime(), nullable=True),
        )

    inspector = sa.inspect(bind)
    reward_indexes = {
        index["name"] for index in inspector.get_indexes("referral_rewards")
    }
    if "ix_referral_rewards_id" not in reward_indexes:
        op.create_index("ix_referral_rewards_id", "referral_rewards", ["id"])
    if "ix_referral_rewards_referrer_user_id" not in reward_indexes:
        op.create_index(
            "ix_referral_rewards_referrer_user_id",
            "referral_rewards",
            ["referrer_user_id"],
        )
    if "ix_referral_rewards_referred_user_id" not in reward_indexes:
        op.create_index(
            "ix_referral_rewards_referred_user_id",
            "referral_rewards",
            ["referred_user_id"],
        )
    if "ix_referral_rewards_purchase_id" not in reward_indexes:
        op.create_index(
            "ix_referral_rewards_purchase_id",
            "referral_rewards",
            ["purchase_id"],
            unique=True,
        )
    if "ix_referral_rewards_status" not in reward_indexes:
        op.create_index("ix_referral_rewards_status", "referral_rewards", ["status"])
    if "ix_referral_rewards_created_at" not in reward_indexes:
        op.create_index("ix_referral_rewards_created_at", "referral_rewards", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_referral_rewards_created_at", table_name="referral_rewards")
    op.drop_index("ix_referral_rewards_status", table_name="referral_rewards")
    op.drop_index("ix_referral_rewards_purchase_id", table_name="referral_rewards")
    op.drop_index("ix_referral_rewards_referred_user_id", table_name="referral_rewards")
    op.drop_index("ix_referral_rewards_referrer_user_id", table_name="referral_rewards")
    op.drop_index("ix_referral_rewards_id", table_name="referral_rewards")
    op.drop_table("referral_rewards")
    op.drop_index("ix_users_referred_by_user_id", table_name="users")
    op.drop_index("ix_users_referral_code", table_name="users")
    op.drop_column("users", "referred_at")
    op.drop_column("users", "referred_by_user_id")
    op.drop_column("users", "referral_code")
