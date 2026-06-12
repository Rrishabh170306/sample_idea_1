"""Full initial schema: all tables + pgvector extension + indexes

Revision ID: 0002_full_initial_schema
Revises: 0001_create_ingestion_and_audit
Create Date: 2026-06-12 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TSVECTOR, JSON

# revision identifiers
revision = '0002_full_initial_schema'
down_revision = '0001_create_ingestion_and_audit'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ------------------------------------------------------------------ schemes
    op.create_table(
        'schemes',
        sa.Column('scheme_id', sa.String(64), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('name_hindi', sa.String(255), nullable=True),
        sa.Column('department', sa.String(255), nullable=True),
        sa.Column('ministry', sa.String(255), nullable=True),
        sa.Column('state', sa.String(64), nullable=True),
        sa.Column('category', sa.JSON(), nullable=True),
        sa.Column('target_beneficiaries', sa.JSON(), nullable=True),
        sa.Column('eligibility', sa.JSON(), nullable=True),
        sa.Column('benefits', sa.JSON(), nullable=True),
        sa.Column('documents_required', sa.JSON(), nullable=True),
        sa.Column('application_process', sa.JSON(), nullable=True),
        sa.Column('official_url', sa.String(500), nullable=True),
        sa.Column('source_url', sa.String(500), nullable=True),
        sa.Column('deadline', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(32), nullable=False, server_default='active'),
        sa.Column('last_updated', sa.DateTime(timezone=True), nullable=True),
        sa.Column('content_hash', sa.String(128), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('crawled_at', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_schemes_state', 'schemes', ['state'])
    op.create_index('ix_schemes_status', 'schemes', ['status'])
    op.create_index('ix_schemes_ministry', 'schemes', ['ministry'])

    # ----------------------------------------------------------- user_profiles
    op.create_table(
        'user_profiles',
        sa.Column('user_id', sa.String(36), primary_key=True),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.Column('gender', sa.String(10), nullable=True),
        sa.Column('state', sa.String(50), nullable=True),
        sa.Column('district', sa.String(100), nullable=True),
        sa.Column('income', sa.Float(), nullable=True),
        sa.Column('occupation', sa.String(100), nullable=True),
        sa.Column('category', sa.String(20), nullable=True),
        sa.Column('education', sa.String(50), nullable=True),
        sa.Column('disability_status', sa.Boolean(), server_default='false'),
        sa.Column('disability_type', sa.String(50), nullable=True),
        sa.Column('land_ownership', sa.Boolean(), server_default='false'),
        sa.Column('land_hectares', sa.Float(), nullable=True),
        sa.Column('business_ownership', sa.Boolean(), server_default='false'),
        sa.Column('business_type', sa.String(50), nullable=True),
        sa.Column('marital_status', sa.String(20), nullable=True),
        sa.Column('dependents', sa.Integer(), nullable=True),
        sa.Column('profile_completeness', sa.Float(), server_default='0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    # ---------------------------------------------------------- user_documents
    op.create_table(
        'user_documents',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('document_type', sa.String(50), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('extracted_data', sa.JSON(), nullable=True),
        sa.Column('verified', sa.Boolean(), server_default='false'),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_user_documents_user_id', 'user_documents', ['user_id'])

    # ----------------------------------------------------------- user_sessions
    op.create_table(
        'user_sessions',
        sa.Column('session_id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('messages', sa.JSON(), nullable=True),
        sa.Column('context', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_user_sessions_user_id', 'user_sessions', ['user_id'])

    # ------------------------------------------------------------- review_queue
    op.create_table(
        'review_queue',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('session_id', sa.String(36), nullable=True),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('response', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('reason', sa.String(50), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('reviewer_id', sa.String(36), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    # ---------------------------------------------------------- scheme_chunks (vector store)
    op.execute("""
        CREATE TABLE scheme_chunks (
            id VARCHAR(36) PRIMARY KEY,
            scheme_id VARCHAR(64) NOT NULL,
            content TEXT NOT NULL,
            chunk_type VARCHAR(20),
            parent_chunk_id VARCHAR(36),
            embedding vector(384),
            search_vector tsvector,
            metadata_json JSON,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.create_index('ix_scheme_chunks_scheme_id', 'scheme_chunks', ['scheme_id'])
    # HNSW index for fast approximate nearest-neighbour search
    op.execute(
        "CREATE INDEX ix_scheme_chunks_embedding ON scheme_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )
    # GIN index for full-text search
    op.execute(
        "CREATE INDEX ix_scheme_chunks_search_vector ON scheme_chunks USING gin(search_vector)"
    )
    # Auto-update search_vector trigger
    op.execute("""
        CREATE OR REPLACE FUNCTION update_search_vector()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector = to_tsvector('english', NEW.content);
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER trig_scheme_chunks_search_vector
        BEFORE INSERT OR UPDATE ON scheme_chunks
        FOR EACH ROW EXECUTE FUNCTION update_search_vector()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trig_scheme_chunks_search_vector ON scheme_chunks")
    op.execute("DROP FUNCTION IF EXISTS update_search_vector()")
    op.drop_table('scheme_chunks')
    op.drop_table('review_queue')
    op.drop_table('user_sessions')
    op.drop_table('user_documents')
    op.drop_table('user_profiles')
    op.drop_table('schemes')
