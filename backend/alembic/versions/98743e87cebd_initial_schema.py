"""initial schema

Revision ID: 98743e87cebd
Revises:
Create Date: 2026-08-15 21:19:46.515659

"""

from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "98743e87cebd"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "profiles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        """
        ALTER TABLE profiles
        ADD CONSTRAINT profiles_id_fkey
        FOREIGN KEY (id) REFERENCES auth.users (id) ON DELETE CASCADE
        """
    )

    op.create_table(
        "source_documents",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("ticker", sa.Text(), nullable=False),
        sa.Column("company_name", sa.Text(), nullable=False),
        sa.Column("filing_type", sa.Text(), nullable=False),
        sa.Column("filing_date", sa.Date(), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("accession_number", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("markdown_content", sa.Text(), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("accession_number"),
    )
    op.create_index(
        op.f("ix_source_documents_fiscal_year"),
        "source_documents",
        ["fiscal_year"],
        unique=False,
    )
    op.create_index(
        op.f("ix_source_documents_ticker"), "source_documents", ["ticker"], unique=False
    )

    op.create_table(
        "chat_threads",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.Text(), server_default="New chat", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_chat_threads_user_id"), "chat_threads", ["user_id"], unique=False
    )

    op.create_table(
        "document_chunks",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("section", sa.Text(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "embedding",
            pgvector.sqlalchemy.vector.VECTOR(dim=1536),
            nullable=False,
        ),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('english', chunk_text)", persisted=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["source_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id", "chunk_index", name="uq_document_chunks_document_index"
        ),
    )
    op.create_index(
        op.f("ix_document_chunks_document_id"),
        "document_chunks",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_chunks_embedding_hnsw",
        "document_chunks",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index(
        "ix_document_chunks_metadata_gin",
        "document_chunks",
        ["metadata"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        "ix_document_chunks_search_vector_gin",
        "document_chunks",
        ["search_vector"],
        unique=False,
        postgresql_using="gin",
    )

    op.create_table(
        "chat_messages",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("thread_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("message", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["thread_id"], ["chat_threads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "thread_id", "sequence", name="uq_chat_messages_thread_sequence"
        ),
    )
    op.create_index(
        op.f("ix_chat_messages_thread_id"), "chat_messages", ["thread_id"], unique=False
    )

    op.create_table(
        "message_citations",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("message_id", sa.UUID(), nullable=False),
        sa.Column("chunk_id", sa.UUID(), nullable=False),
        sa.Column("citation_label", sa.Text(), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["chat_messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_message_citations_chunk_id"),
        "message_citations",
        ["chunk_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_message_citations_message_id"),
        "message_citations",
        ["message_id"],
        unique=False,
    )

    for table in (
        "profiles",
        "chat_threads",
        "chat_messages",
        "message_citations",
        "source_documents",
        "document_chunks",
    ):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    op.execute(
        """
        CREATE POLICY profiles_select_own ON profiles
        FOR SELECT TO authenticated
        USING (auth.uid() = id)
        """
    )
    op.execute(
        """
        CREATE POLICY profiles_insert_own ON profiles
        FOR INSERT TO authenticated
        WITH CHECK (auth.uid() = id)
        """
    )
    op.execute(
        """
        CREATE POLICY profiles_update_own ON profiles
        FOR UPDATE TO authenticated
        USING (auth.uid() = id)
        WITH CHECK (auth.uid() = id)
        """
    )

    op.execute(
        """
        CREATE POLICY chat_threads_owner ON chat_threads
        FOR ALL TO authenticated
        USING (auth.uid() = user_id)
        WITH CHECK (auth.uid() = user_id)
        """
    )

    op.execute(
        """
        CREATE POLICY chat_messages_thread_owner ON chat_messages
        FOR ALL TO authenticated
        USING (
            EXISTS (
                SELECT 1 FROM chat_threads t
                WHERE t.id = chat_messages.thread_id AND t.user_id = auth.uid()
            )
        )
        WITH CHECK (
            EXISTS (
                SELECT 1 FROM chat_threads t
                WHERE t.id = chat_messages.thread_id AND t.user_id = auth.uid()
            )
        )
        """
    )

    op.execute(
        """
        CREATE POLICY message_citations_thread_owner ON message_citations
        FOR ALL TO authenticated
        USING (
            EXISTS (
                SELECT 1
                FROM chat_messages m
                JOIN chat_threads t ON t.id = m.thread_id
                WHERE m.id = message_citations.message_id AND t.user_id = auth.uid()
            )
        )
        WITH CHECK (
            EXISTS (
                SELECT 1
                FROM chat_messages m
                JOIN chat_threads t ON t.id = m.thread_id
                WHERE m.id = message_citations.message_id AND t.user_id = auth.uid()
            )
        )
        """
    )

    op.execute(
        """
        CREATE POLICY source_documents_read ON source_documents
        FOR SELECT TO authenticated
        USING (true)
        """
    )
    op.execute(
        """
        CREATE POLICY document_chunks_read ON document_chunks
        FOR SELECT TO authenticated
        USING (true)
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS document_chunks_read ON document_chunks")
    op.execute("DROP POLICY IF EXISTS source_documents_read ON source_documents")
    op.execute("DROP POLICY IF EXISTS message_citations_thread_owner ON message_citations")
    op.execute("DROP POLICY IF EXISTS chat_messages_thread_owner ON chat_messages")
    op.execute("DROP POLICY IF EXISTS chat_threads_owner ON chat_threads")
    op.execute("DROP POLICY IF EXISTS profiles_update_own ON profiles")
    op.execute("DROP POLICY IF EXISTS profiles_insert_own ON profiles")
    op.execute("DROP POLICY IF EXISTS profiles_select_own ON profiles")

    op.drop_index(op.f("ix_message_citations_message_id"), table_name="message_citations")
    op.drop_index(op.f("ix_message_citations_chunk_id"), table_name="message_citations")
    op.drop_table("message_citations")
    op.drop_index(op.f("ix_chat_messages_thread_id"), table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index(
        "ix_document_chunks_search_vector_gin",
        table_name="document_chunks",
        postgresql_using="gin",
    )
    op.drop_index(
        "ix_document_chunks_metadata_gin",
        table_name="document_chunks",
        postgresql_using="gin",
    )
    op.drop_index(
        "ix_document_chunks_embedding_hnsw",
        table_name="document_chunks",
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.drop_index(op.f("ix_document_chunks_document_id"), table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_index(op.f("ix_chat_threads_user_id"), table_name="chat_threads")
    op.drop_table("chat_threads")
    op.drop_index(op.f("ix_source_documents_ticker"), table_name="source_documents")
    op.drop_index(op.f("ix_source_documents_fiscal_year"), table_name="source_documents")
    op.drop_table("source_documents")
    op.execute("ALTER TABLE profiles DROP CONSTRAINT IF EXISTS profiles_id_fkey")
    op.drop_table("profiles")
