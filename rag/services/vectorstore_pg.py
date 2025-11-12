from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
import psycopg2.extras
import json

class CustomPGVector:
    def __init__(self, db, embedding_fn, table: str = "medical"):
        self.db = db
        self.embedding_fn = embedding_fn
        self.table = table

    def add_documents(self, docs: List[Document]):
        """문서를 임베딩 후 pgvector 테이블에 저장"""
        if not docs:
            print("⚠️ 저장할 문서가 없습니다.")
            return

        texts = [d.page_content for d in docs]
        embeddings = self.embedding_fn.embed_documents(texts)

        conn = self.db.get_connection()
        try:
            with conn.cursor() as cur:
                for doc, emb in zip(docs, embeddings):
                    cur.execute(
                        f"""
                        INSERT INTO {self.table} (content, embedding, metadata)
                        VALUES (%s, %s::vector, %s)
                        """,
                        (doc.page_content, emb, psycopg2.extras.Json(doc.metadata))
                    )
            conn.commit()
            print(f"✅ {len(docs)}개 문서 임베딩 및 저장 완료.")
        finally:
            self.db.put_connection(conn)
