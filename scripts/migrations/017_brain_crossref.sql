-- Migration 017: Cross-source semantic matching
-- Fixes: brain_search HNSW index can't find matches across different source_tables
-- because the HNSW graph has disconnected clusters per domain.
-- This function widens the HNSW search (ef_search=400) for cross-source comparisons.

CREATE OR REPLACE FUNCTION brain_crossref(
    source_a text,
    source_b text,
    sample_limit int DEFAULT 30,
    match_per_chunk int DEFAULT 3,
    min_similarity float DEFAULT 0.5
)
RETURNS TABLE (
    source_a_id TEXT,
    title_a TEXT,
    text_a TEXT,
    metadata_a JSONB,
    chunk_index_a INTEGER,
    source_b_id TEXT,
    title_b TEXT,
    text_b TEXT,
    metadata_b JSONB,
    chunk_index_b INTEGER,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Widen HNSW search to find cross-domain matches
    -- Default ef_search=40 only finds same-domain neighbors
    SET LOCAL hnsw.ef_search = 400;

    RETURN QUERY
    SELECT
        a.source_id,
        a.title,
        a.chunk_text,
        a.metadata,
        a.chunk_index,
        b.source_id,
        b.title,
        b.chunk_text,
        b.metadata,
        b.chunk_index,
        (1 - (a.embedding <=> b.embedding))::float as sim
    FROM (
        -- Sample from source A (first chunk per document = most representative)
        SELECT bc.source_id, bc.title, bc.chunk_text, bc.metadata, bc.chunk_index, bc.embedding
        FROM brain_chunks bc
        WHERE bc.source_table = source_a
          AND bc.embedding IS NOT NULL
          AND bc.chunk_index = 0
        LIMIT sample_limit
    ) a
    CROSS JOIN LATERAL (
        -- For each source A chunk, find nearest matches in source B
        SELECT bc.source_id, bc.title, bc.chunk_text, bc.metadata, bc.chunk_index, bc.embedding
        FROM brain_chunks bc
        WHERE bc.source_table = source_b
          AND bc.embedding IS NOT NULL
        ORDER BY bc.embedding <=> a.embedding
        LIMIT match_per_chunk
    ) b
    WHERE (1 - (a.embedding <=> b.embedding)) >= min_similarity
    ORDER BY (1 - (a.embedding <=> b.embedding)) DESC;
END;
$$;

COMMENT ON FUNCTION brain_crossref IS 'Cross-source semantic matching with widened HNSW search. Use for finding overlaps between patent claims ↔ FCC filings, etc.';
