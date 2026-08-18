-- Xebia Proposal Studio — Initial Schema
-- Run this after creating the database and enabling pgvector:
--   CREATE DATABASE xebia_proposal_studio;
--   \c xebia_proposal_studio
--   CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- REFERENCE LIBRARY
-- ============================================================

CREATE TABLE IF NOT EXISTS documents (
    id              SERIAL PRIMARY KEY,
    filename        TEXT NOT NULL,
    file_path       TEXT NOT NULL,
    file_type       TEXT NOT NULL CHECK (file_type IN ('pptx', 'docx', 'pdf')),
    file_size_bytes BIGINT,
    content_hash    TEXT NOT NULL,

    -- Classification
    document_type   TEXT,           -- proposal, case_study, workshop, etc.
    proposal_type   TEXT,           -- rfp_response, technical_proposal, etc.
    industries      TEXT[],
    technologies    TEXT[],

    -- Governance
    approval_status TEXT NOT NULL DEFAULT 'pending_review'
        CHECK (approval_status IN ('pending_review', 'approved', 'restricted', 'archived')),
    confidentiality TEXT NOT NULL DEFAULT 'internal'
        CHECK (confidentiality IN ('public', 'internal', 'confidential', 'restricted')),
    reusable        BOOLEAN NOT NULL DEFAULT true,

    -- Metadata from file properties
    title           TEXT,
    author          TEXT,
    last_modified_by TEXT,
    file_created_at TIMESTAMPTZ,
    file_modified_at TIMESTAMPTZ,

    -- System
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (content_hash)
);

CREATE INDEX idx_documents_type ON documents (document_type);
CREATE INDEX idx_documents_proposal_type ON documents (proposal_type);
CREATE INDEX idx_documents_approval ON documents (approval_status);
CREATE INDEX idx_documents_industries ON documents USING GIN (industries);
CREATE INDEX idx_documents_technologies ON documents USING GIN (technologies);


-- ============================================================
-- SLIDES (PPT)
-- ============================================================

CREATE TABLE IF NOT EXISTS slides (
    id              SERIAL PRIMARY KEY,
    document_id     INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    slide_number    INTEGER NOT NULL,

    -- Content
    text_content    TEXT,
    word_count      INTEGER DEFAULT 0,
    notes           TEXT,

    -- Classification
    slide_type      TEXT,           -- cover, executive_summary, solution, etc.
    content_density TEXT CHECK (content_density IN ('low', 'medium', 'high')),
    visual_density  TEXT CHECK (visual_density IN ('low', 'medium', 'high')),

    -- Visual metadata
    image_count     INTEGER DEFAULT 0,
    table_count     INTEGER DEFAULT 0,
    chart_count     INTEGER DEFAULT 0,
    has_diagram     BOOLEAN DEFAULT false,

    -- Raw extracted data
    raw_data        JSONB,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (document_id, slide_number)
);

CREATE INDEX idx_slides_document ON slides (document_id);
CREATE INDEX idx_slides_type ON slides (slide_type);


-- ============================================================
-- SECTIONS (DOCX)
-- ============================================================

CREATE TABLE IF NOT EXISTS sections (
    id              SERIAL PRIMARY KEY,
    document_id     INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    section_index   INTEGER NOT NULL,

    heading         TEXT,
    heading_level   INTEGER,
    text_content    TEXT,
    word_count      INTEGER DEFAULT 0,

    raw_data        JSONB,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (document_id, section_index)
);

CREATE INDEX idx_sections_document ON sections (document_id);


-- ============================================================
-- TAGS
-- ============================================================

CREATE TABLE IF NOT EXISTS tags (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    category        TEXT           -- industry, technology, topic, etc.
);

CREATE TABLE IF NOT EXISTS document_tags (
    document_id     INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    tag_id          INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (document_id, tag_id)
);


-- ============================================================
-- EMBEDDINGS (pgvector)
-- ============================================================

CREATE TABLE IF NOT EXISTS embeddings (
    id              SERIAL PRIMARY KEY,
    entity_type     TEXT NOT NULL CHECK (entity_type IN ('slide', 'section', 'document')),
    entity_id       INTEGER NOT NULL,
    embedding_type  TEXT NOT NULL DEFAULT 'content'
        CHECK (embedding_type IN ('content', 'layout', 'visual')),

    model_name      TEXT NOT NULL,
    model_version   TEXT,
    dimensions      INTEGER NOT NULL,
    embedding       vector(384),

    content_hash    TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (entity_type, entity_id, embedding_type, model_name)
);

CREATE INDEX idx_embeddings_entity ON embeddings (entity_type, entity_id);
CREATE INDEX idx_embeddings_vector ON embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);


-- ============================================================
-- PROPOSALS (Generated output tracking)
-- ============================================================

CREATE TABLE IF NOT EXISTS proposals (
    id              SERIAL PRIMARY KEY,
    title           TEXT NOT NULL,
    customer        TEXT,
    industry        TEXT,
    proposal_type   TEXT,
    objective       TEXT,

    -- Plan
    storyline       TEXT[],
    plan_data       JSONB,

    -- Status
    status          TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'generating', 'review', 'approved', 'final')),

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE TABLE IF NOT EXISTS proposal_references (
    id              SERIAL PRIMARY KEY,
    proposal_id     INTEGER NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,
    document_id     INTEGER NOT NULL REFERENCES documents(id),
    reference_type  TEXT NOT NULL CHECK (reference_type IN ('content', 'layout', 'style')),

    entity_type     TEXT,           -- slide, section
    entity_id       INTEGER,
    relevance_score REAL,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_proposal_refs_proposal ON proposal_references (proposal_id);


CREATE TABLE IF NOT EXISTS proposal_outputs (
    id              SERIAL PRIMARY KEY,
    proposal_id     INTEGER NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,
    output_type     TEXT NOT NULL CHECK (output_type IN ('pptx', 'docx', 'pdf')),
    file_path       TEXT NOT NULL,
    file_size_bytes BIGINT,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- QA RESULTS
-- ============================================================

CREATE TABLE IF NOT EXISTS qa_results (
    id              SERIAL PRIMARY KEY,
    proposal_id     INTEGER REFERENCES proposals(id) ON DELETE CASCADE,
    output_id       INTEGER REFERENCES proposal_outputs(id) ON DELETE CASCADE,

    qa_type         TEXT NOT NULL CHECK (qa_type IN ('structural', 'visual', 'brand', 'content', 'proposal')),
    status          TEXT NOT NULL CHECK (status IN ('pass', 'warning', 'fail')),
    findings        JSONB,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_qa_proposal ON qa_results (proposal_id);


-- ============================================================
-- SLIDE PATTERNS (reusable layout patterns)
-- ============================================================

CREATE TABLE IF NOT EXISTS slide_patterns (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    category        TEXT NOT NULL,     -- cover, executive_summary, architecture, etc.
    description     TEXT,
    layout_data     JSONB,             -- shape positions, sizes, types
    example_slides  INTEGER[],         -- references to slide IDs

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_patterns_category ON slide_patterns (category);
