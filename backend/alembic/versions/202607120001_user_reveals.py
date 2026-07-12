"""user reveal table

Revision ID: 202607120001
Revises: 202607050001
Create Date: 2026-07-12
"""

from alembic import op
import sqlalchemy as sa


revision = "202607120001"
down_revision = "202607050001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "user_reveals" not in tables:
        op.create_table(
            "user_reveals",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("viewer_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("revealed_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("context_type", sa.String(length=64), nullable=False),
            sa.Column("context_id", sa.String(length=64), nullable=False),
            sa.Column("target_role", sa.String(length=32), nullable=False),
            sa.Column("price_units", sa.BigInteger(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint(
                "viewer_user_id",
                "context_type",
                "context_id",
                "target_role",
                name="uq_user_reveal_viewer_context_target",
            ),
        )

    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("user_reveals")}

    if "ix_user_reveals_id" not in indexes:
        op.create_index("ix_user_reveals_id", "user_reveals", ["id"])
    if "ix_user_reveals_viewer_user_id" not in indexes:
        op.create_index(
            "ix_user_reveals_viewer_user_id",
            "user_reveals",
            ["viewer_user_id"],
        )
    if "ix_user_reveals_revealed_user_id" not in indexes:
        op.create_index(
            "ix_user_reveals_revealed_user_id",
            "user_reveals",
            ["revealed_user_id"],
        )
    if "ix_user_reveals_context_type" not in indexes:
        op.create_index(
            "ix_user_reveals_context_type",
            "user_reveals",
            ["context_type"],
        )
    if "ix_user_reveals_context_id" not in indexes:
        op.create_index(
            "ix_user_reveals_context_id",
            "user_reveals",
            ["context_id"],
        )
    if "ix_user_reveals_target_role" not in indexes:
        op.create_index(
            "ix_user_reveals_target_role",
            "user_reveals",
            ["target_role"],
        )
    if "ix_user_reveals_created_at" not in indexes:
        op.create_index(
            "ix_user_reveals_created_at",
            "user_reveals",
            ["created_at"],
        )


def downgrade() -> None:
    op.drop_index("ix_user_reveals_created_at", table_name="user_reveals")
    op.drop_index("ix_user_reveals_target_role", table_name="user_reveals")
    op.drop_index("ix_user_reveals_context_id", table_name="user_reveals")
    op.drop_index("ix_user_reveals_context_type", table_name="user_reveals")
    op.drop_index("ix_user_reveals_revealed_user_id", table_name="user_reveals")
    op.drop_index("ix_user_reveals_viewer_user_id", table_name="user_reveals")
    op.drop_index("ix_user_reveals_id", table_name="user_reveals")
    op.drop_table("user_reveals")
