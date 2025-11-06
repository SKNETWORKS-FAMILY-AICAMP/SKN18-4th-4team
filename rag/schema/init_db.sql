 -- doc/chunk/embedding 테이블, 인덱스


 CREATE EXTENSION IF NOT EXISTS vector;

-- test
CREATE TABLE IF NOT EXISTS docs (
  doc_id BIGSERIAL PRIMARY KEY,
  title TEXT,
  source TEXT,
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
  chunk_id BIGSERIAL PRIMARY KEY,
  doc_id BIGINT REFERENCES docs(doc_id) ON DELETE CASCADE,
  content TEXT,
  embedding vector(768),
  meta JSONB,
  created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chunks_embed
  ON chunks USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
