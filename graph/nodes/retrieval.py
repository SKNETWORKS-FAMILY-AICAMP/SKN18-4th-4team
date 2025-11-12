# nodes/retrieval.py
from langchain_community.vectorstores.pgvector import PGVector
from graph.state import SelfRAGState


def retrieval(state: SelfRAGState, vectorstore: PGVector) -> SelfRAGState:
    """
    Retrieval 노드
    pgvector에서 관련 문서 검색
    """
    query = state.get("question", "").strip()

    try:
        # vectorstore에서 유사도 검색 (상위 5개)
        docs = vectorstore.similarity_search_with_score(query, k=5)

        # 문서 정보 추출
        retrieved_docs = []
        context_parts = []
        sources = []
        seen_c_ids = set()  # 중복 체크용

        for i, (doc, score) in enumerate(docs, 1):
            doc_info = {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": score
            }
            retrieved_docs.append(doc_info)

            # 컨텍스트 구성
            context_parts.append(f"[문서 {i}] (관련도: {score:.2f})\n{doc.page_content}")

            # 출처 정보 - c_id 사용 (중복 제거)
            c_id = doc.metadata.get("c_id", f"문서_{i}")
            if c_id not in seen_c_ids:
                sources.append(f"[{i}] {c_id}")
                seen_c_ids.add(c_id)

        state["retrieved_docs"] = retrieved_docs
        state["context"] = "\n\n".join(context_parts)
        state["sources"] = sources

    except Exception as e:
        # 검색 실패 시
        state["retrieved_docs"] = []
        state["context"] = ""
        state["sources"] = []
        print(f"문서 검색 오류: {e}")

    return state
