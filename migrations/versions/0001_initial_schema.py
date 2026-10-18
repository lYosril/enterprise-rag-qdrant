"""initial schema: documents, conversations, messages

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-16

Baseline migration that materialises the core tables the application has always
required. It intentionally excludes ownership columns (``owner_id``) and the
``users`` table, which are added by ``a1b2c3d4e5f6``. Keeping the two steps
separate preserves the real migration history for databases that predate
multi-tenancy.

The upgrade is written defensively: it skips a table that already exists so it
can be applied to databases originally created with ``Base.metadata.create_all``
without error.

On a fresh database ``alembic upgrade head`` runs this revision first. On a
legacy database already stamped ``a1b2c3d4e5f6`` this revision is skipped (it is
an ancestor of the current revision), so no work is repeated.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    return sa.inspect(bind).has_table(name)


def upgrade() -> None:
    if not _has_table("documents"):
        op.create_table(
            "documents",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("filename", sa.String(length=255), nullable=False),
            sa.Column("stored_path", sa.String(length=1000), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table("conversations"):
        op.create_table(
            "conversations",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table("messages"):
        op.create_table(
            "messages",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "conversation_id",
                postgresql.UUID(as_uuid=True),
                nullable=False,
            ),
            sa.Column("role", sa.String(length=20), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("sources", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.ForeignKeyConstraint(
                ["conversation_id"], ["conversations.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_messages_conversation_id"),
            "messages",
            ["conversation_id"],
            unique=False,
        )


def downgrade() -> None:
    if _has_table("messages"):
        op.drop_index(op.f("ix_messages_conversation_id"), table_name="messages")
        op.drop_table("messages")
    if _has_table("conversations"):
        op.drop_table("conversations")
    if _has_table("documents"):
        op.drop_table("documents")
