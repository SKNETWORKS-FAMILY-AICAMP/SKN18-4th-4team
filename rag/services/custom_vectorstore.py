# custom_vectorstore.py
"""
sknproject4 데이터베이스의 medical 테이블을 사용하는 커스텀 vectorstore
"""
import os
from typing import List, Tuple
from dotenv import load_dotenv
import psycopg2
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
import numpy as np

load_dotenv()


class CustomVectorStore:
    """
    medical 테이블을 사용하는 커스텀 vectorstore

    테이블 구조:
    - id: bigint (기본 키)
    - content: text (문서 텍스트)
    - embedding: vector (임베딩 벡터)
    - metadata: jsonb (메타데이터, c_id 포함)
    """

    def __init__(self):
        # 데이터베이스 연결 정보
        self.db_user = os.getenv("POSTGRES_USER", "root")
        self.db_password = os.getenv("POSTGRES_PASSWORD", "root1234")
        self.db_host = os.getenv("POSTGRES_HOST", "localhost")
        self.db_port = os.getenv("POSTGRES_PORT", "5432")
        self.db_name = os.getenv("POSTGRES_DB", "sknproject4")

        # 연결 문자열
        self.connection_string = f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

        # OpenAI 임베딩 모델
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )

        # 거리 메트릭 (cosine distance)
        self.distance_metric = os.getenv("PGVECTOR_DISTANCE", "cosine")

    def _get_connection(self):
        """데이터베이스 연결 생성"""
        return psycopg2.connect(self.connection_string)

    def _cosine_distance_sql(self) -> str:
        """코사인 거리 계산 SQL"""
        return "1 - (embedding <=> %s::vector)"

    def _euclidean_distance_sql(self) -> str:
        """유클리드 거리 계산 SQL"""
        return "embedding <-> %s::vector"

    def _get_distance_sql(self) -> str:
        """설정된 거리 메트릭에 따른 SQL 반환"""
        if self.distance_metric == "cosine":
            return self._cosine_distance_sql()
        else:
            return self._euclidean_distance_sql()

    def similarity_search(self, query: str, k: int = 5) -> List[Document]:
        """
        쿼리와 유사한 문서 검색

        Args:
            query: 검색 쿼리
            k: 반환할 문서 수

        Returns:
            Document 리스트
        """
        # 쿼리 임베딩 생성
        query_embedding = self.embeddings.embed_query(query)

        # 벡터를 PostgreSQL 포맷으로 변환
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

        # 유사도 검색 SQL
        distance_sql = self._get_distance_sql()
        sql = f"""
            SELECT
                id,
                metadata->>'c_id' as c_id,
                content,
                {distance_sql} as similarity
            FROM medical
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # distance_sql에 1개, ORDER BY에 1개, LIMIT에 1개 = 총 3개 파라미터
                cur.execute(sql, (embedding_str, embedding_str, k))
                results = cur.fetchall()

        # Document 객체로 변환
        documents = []
        for row in results:
            doc_id, c_id, content, similarity = row
            documents.append(
                Document(
                    page_content=content,
                    metadata={
                        "id": doc_id,
                        "c_id": c_id,
                        "similarity": float(similarity) if similarity else None
                    }
                )
            )

        return documents

    def similarity_search_with_score(self, query: str, k: int = 5) -> List[Tuple[Document, float]]:
        """
        쿼리와 유사한 문서 검색 (점수 포함)

        Args:
            query: 검색 쿼리
            k: 반환할 문서 수

        Returns:
            (Document, score) 튜플 리스트
        """
        # 쿼리 임베딩 생성
        query_embedding = self.embeddings.embed_query(query)

        # 벡터를 PostgreSQL 포맷으로 변환
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

        # 유사도 검색 SQL
        distance_sql = self._get_distance_sql()
        sql = f"""
            SELECT
                id,
                metadata->>'c_id' as c_id,
                content,
                {distance_sql} as similarity
            FROM medical
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # distance_sql에 1개, ORDER BY에 1개, LIMIT에 1개 = 총 3개 파라미터
                cur.execute(sql, (embedding_str, embedding_str, k))
                results = cur.fetchall()

        # Document 객체와 점수로 변환
        documents_with_scores = []
        for row in results:
            doc_id, c_id, content, similarity = row
            doc = Document(
                page_content=content,
                metadata={
                    "id": doc_id,
                    "c_id": c_id
                }
            )
            score = float(similarity) if similarity else 0.0
            documents_with_scores.append((doc, score))

        return documents_with_scores

    def max_marginal_relevance_search(
        self,
        query: str,
        k: int = 5,
        fetch_k: int = 20,
        lambda_mult: float = 0.5
    ) -> List[Document]:
        """
        MMR (Maximal Marginal Relevance) 검색
        다양성을 고려한 검색 결과 반환

        Args:
            query: 검색 쿼리
            k: 반환할 문서 수
            fetch_k: 초기 후보 문서 수
            lambda_mult: 관련성과 다양성의 균형 (0~1)

        Returns:
            Document 리스트
        """
        # 초기 후보 문서 가져오기
        candidates = self.similarity_search_with_score(query, k=fetch_k)

        if not candidates:
            return []

        # 쿼리 임베딩
        query_embedding = np.array(self.embeddings.embed_query(query))

        # 선택된 문서와 임베딩
        selected_docs = []
        selected_embeddings = []

        # 후보 문서와 임베딩
        candidate_docs = [doc for doc, _ in candidates]
        candidate_texts = [doc.page_content for doc in candidate_docs]
        candidate_embeddings = self.embeddings.embed_documents(candidate_texts)

        while len(selected_docs) < k and candidate_docs:
            best_score = -float('inf')
            best_idx = 0

            for i, (doc, emb) in enumerate(zip(candidate_docs, candidate_embeddings)):
                # 쿼리와의 유사도
                query_sim = np.dot(query_embedding, emb) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(emb)
                )

                # 이미 선택된 문서들과의 최대 유사도
                if selected_embeddings:
                    max_sim = max(
                        np.dot(emb, sel_emb) / (np.linalg.norm(emb) * np.linalg.norm(sel_emb))
                        for sel_emb in selected_embeddings
                    )
                else:
                    max_sim = 0

                # MMR 점수 계산
                mmr_score = lambda_mult * query_sim - (1 - lambda_mult) * max_sim

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = i

            # 최고 점수 문서 선택
            selected_docs.append(candidate_docs[best_idx])
            selected_embeddings.append(candidate_embeddings[best_idx])

            # 후보에서 제거
            candidate_docs.pop(best_idx)
            candidate_embeddings.pop(best_idx)

        return selected_docs


def create_vectorstore():
    """
    커스텀 vectorstore 생성
    """
    return CustomVectorStore()


if __name__ == "__main__":
    # 테스트
    try:
        vectorstore = create_vectorstore()
        print("✅ 커스텀 vectorstore 생성 성공!")

        # 검색 테스트
        test_query = "대장암 치료"
        results = vectorstore.similarity_search(test_query, k=3)

        print(f"\n검색 쿼리: {test_query}")
        print(f"검색 결과 수: {len(results)}")

        for i, doc in enumerate(results, 1):
            print(f"\n{i}. [{doc.metadata.get('c_id')}]")
            print(f"   내용: {doc.page_content[:100]}...")
            print(f"   유사도: {doc.metadata.get('similarity', 'N/A')}")

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
