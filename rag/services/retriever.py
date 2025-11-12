

from dataclasses import dataclass
from typing import List, Optional

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
    table_name: str = "t3_chunks"
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
                id,
                c_id,
                chunk_text,
                embedding <=> %s AS distance
            FROM {self.table_name}
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s
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
        for doc_id, c_id, chunk_text, distance in rows:
            similarity = 1.0 - float(distance) if distance is not None else None
            if threshold is not None and similarity is not None and similarity < threshold:
                continue

            docs.append(
                Document(
                    page_content=chunk_text,
                    metadata={
                        "id": doc_id,
                        "c_id": c_id,
                        "distance": float(distance),
                        "similarity": similarity,
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



























# from .embedder import get_embedding, get_pg_conn



# def search_top_k(query_text: str, top_k: int = 10):
#     """
#     query_text를 임베딩한 후,
#     Postgres(pgvector)의 코사인 거리(<=>)를 이용해서
#     가장 유사한 row TOP_K를 가져오는 함수
#     (※ 리랭킹은 별도 Ranker에서)
#     """
#     # 1) 쿼리 문장 임베딩
#     query_vec = get_embedding(query_text)

#     # 2) DB 접속 후 코사인 거리로 정렬해서 TOP_K 뽑기
#     conn = get_pg_conn()
#     try:    
#         with conn.cursor() as cur:
#             sql = """
#                 SELECT
#                     id,
#                     c_id,
#                     chunk_text,
#                     embedding <=> %s AS distance   -- 코사인 거리
#                 FROM t3_chunks                     -- 테이블 명
#                 WHERE embedding IS NOT NULL        -- 임베딩 된 것만
#                 ORDER BY embedding <=> %s
#                 LIMIT %s;
#             """
#             # 같은 벡터를 두 번 쓰기 때문에 %s 자리에 query_vec, query_vec, top_k
#             cur.execute(sql, (query_vec, query_vec, top_k))
#             rows = cur.fetchall()

#         # rows: [(id, title, content, distance), ...]
#         return rows
#     finally:
#         conn.close()



# class VectorStore:
#     """
#     기존 search_top_k 함수를 래핑한 간단한 vectorstore 클래스
#     LangChain의 similarity_search 인터페이스 호환
#     """

#     def __init__(self):
#         """연결 테스트"""
#         conn = get_pg_conn()
#         conn.close()

#     def similarity_search(self, query: str, k: int = 5):
#         """
#         유사도 검색 수행

#         Args:
#             query: 검색 질의
#             k: 반환할 문서 개수

#         Returns:
#             list: 검색 결과 리스트 [(id, c_id, chunk_text, distance), ...]
#         """
#         return search_top_k(query, top_k=k)


# def create_vectorstore():
#     """
#     vectorstore 인스턴스를 생성하고 연결을 테스트합니다.
#     기존 search_top_k 기반으로 동작합니다.

#     Returns:
#         SimpleVectorStore: vectorstore 인스턴스

#     Raises:
#         Exception: DB 연결 실패 시
#     """
#     return VectorStore()