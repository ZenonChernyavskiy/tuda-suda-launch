"""admin statistics indexes

Revision ID: 202607150001
Revises: 202607120001
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa


revision = "202607150001"
down_revision = "202607120001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    indexes = {index["name"] for index in inspector.get_indexes("users")}

    if "ix_users_created_at" not in indexes:
        op.create_index("ix_users_created_at", "users", ["created_at"])
    if "ix_users_last_active_at" not in indexes:
        op.create_index("ix_users_last_active_at", "users", ["last_active_at"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    indexes = {index["name"] for index in inspector.get_indexes("users")}

    if "ix_users_last_active_at" in indexes:
        op.drop_index("ix_users_last_active_at", table_name="users")
    if "ix_users_created_at" in indexes:
        op.drop_index("ix_users_created_at", table_name="users")
