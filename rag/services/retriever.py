

from dataclasses import dataclass
from typing import List, Optional
import json

from langchain_core.documents import Document

# 상대 import와 절대 import를 모두 지원 (Jupyter 노트북에서도 동작하도록)
try:
    from .embedder import get_embedding, get_pg_conn
except ImportError:
    # 상대 import가 실패하면 절대 import 시도 (패키지 외부에서 실행될 때)
    try:
        from rag.services.embedder import get_embedding, get_pg_conn
    except ImportError:
        # 같은 디렉토리에서 직접 실행될 때 (Jupyter 노트북 등)
        from embedder import get_embedding, get_pg_conn


@dataclass(slots=True)
class VectorRetriever:
    table_name: str = "medical"
    default_k: int = 5
    min_similarity: Optional[float] = None

    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        min_similarity: Optional[float] = None,
    ) -> List[Document]:
        k = top_k or self.default_k
        threshold = (
            min_similarity if min_similarity is not None else self.min_similarity
        )

        query_vec = get_embedding(query)
        sql = f"""
            SELECT
                content,
                metadata,
                embedding <=> %s::vector AS distance
            FROM {self.table_name}
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
        """

        conn = get_pg_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (query_vec, query_vec, k))
                rows = cur.fetchall()
        finally:
            conn.close()

        docs: List[Document] = []
        for content, metadata, distance in rows:
            # 코사인 거리(distance)를 유사도(similarity)로 변환
            # distance: 0에 가까울수록 유사, 1에 가까울수록 비유사
            # similarity: 1에 가까울수록 유사, 0에 가까울수록 비유사 (사용자가 보기에 더 직관적)
            similarity = 1.0 - float(distance) if distance is not None else None
            
            # 최소 유사도 임계값 필터링
            if threshold is not None and similarity is not None and similarity < threshold:
                continue

            # metadata가 JSONB이므로 dict로 파싱하여 c_id 추출
            c_id = None
            if metadata and isinstance(metadata, dict):
                c_id = metadata.get("c_id")
            elif metadata and isinstance(metadata, str):
                # 문자열인 경우 JSON 파싱 시도
                try:
                    metadata_dict = json.loads(metadata)
                    c_id = metadata_dict.get("c_id") if isinstance(metadata_dict, dict) else None
                except (json.JSONDecodeError, TypeError):
                    pass

            # 사용자와 LLM에게 전달할 Document 생성
            # 유사도 정보를 포함하여 더 직관적인 정보 제공
            docs.append(
                Document(
                    page_content=content,
                    metadata={
                        "c_id": c_id,
                        "similarity": similarity,  # 거리 대신 유사도로 전달
                    },
                )
            )
        return docs


_retriever: Optional[VectorRetriever] = None


def get_vector_retriever() -> VectorRetriever:
    global _retriever
    if _retriever is None:
        _retriever = VectorRetriever()
    return _retriever