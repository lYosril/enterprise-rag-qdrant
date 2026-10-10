"""add users and resource ownership

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-10-10

Adds the users table, then nullable owner_id foreign keys on documents and
conversations. Legacy rows keep owner_id NULL until you assign owners
deliberately; do not backfill with a placeholder user.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.add_column(
        "documents",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        op.f("ix_documents_owner_id"),
        "documents",
        ["owner_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_documents_owner_id_users",
        "documents",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.add_column(
        "conversations",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        op.f("ix_conversations_owner_id"),
        "conversations",
        ["owner_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_conversations_owner_id_users",
        "conversations",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_conversations_owner_id_users",
        "conversations",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_conversations_owner_id"), table_name="conversations")
    op.drop_column("conversations", "owner_id")

    op.drop_constraint(
        "fk_documents_owner_id_users",
        "documents",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_documents_owner_id"), table_name="documents")
    op.drop_column("documents", "owner_id")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
