"""create document_chunks

Revision ID: 0002_document_chunks
Revises: a1b2c3d4e5f6
Create Date: 2026-10-16

Creates the ``document_chunks`` table used to persist the exact text and page
numbers of every embedded chunk. The table carries ``owner_id`` because chunk
retrieval is scoped to the owning user, so it must be created after the
``users`` table exists (added by ``a1b2c3d4e5f6``).

Idempotent: databases that already contain ``document_chunks`` are left
untouched.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_document_chunks"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    return sa.inspect(bind).has_table(name)


def upgrade() -> None:
    if _has_table("document_chunks"):
        return

    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_document_chunks_document_id"),
        "document_chunks",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_chunks_owner_id"),
        "document_chunks",
        ["owner_id"],
        unique=False,
    )


def downgrade() -> None:
    if _has_table("document_chunks"):
        op.drop_index(
            op.f("ix_document_chunks_owner_id"), table_name="document_chunks"
        )
        op.drop_index(
            op.f("ix_document_chunks_document_id"), table_name="document_chunks"
        )
        op.drop_table("document_chunks")
