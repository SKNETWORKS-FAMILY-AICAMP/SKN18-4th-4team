from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings


def retriever(state, vectorstore, k: int = 5):
    """
    사용자의 질문(query)을 벡터 임베딩으로 변환하고,
    medical_documents 벡터 DB에서 코사인 유사도 기반으로
    상위 k개의 관련 문서를 검색하는 LangGraph 노드.
    """

    query_type = state.get("query_type", "")
    query = state.get("user_input", "").strip()

    # --- 1️⃣ RAG 대상이 아닌 경우 ---
    if query_type != "answerable" or not query:
        state["retrieved_docs"] = []
        state["message"] = "질문이 RAG 도메인과 무관하거나 비어 있습니다."
        return state

    # --- 2️⃣ 쿼리 임베딩 생성 ---
    embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
    query_vector = embedding_model.embed_query(query)

    # --- 3️⃣ 유사도 검색 (코사인 유사도 기반) ---
    try:
        results = vectorstore.similarity_search_by_vector(query_vector, k=k)
    except Exception as e:
        state["retrieved_docs"] = []
        state["message"] = f"벡터 검색 중 오류 발생: {e}"
        return state

    # --- 4️⃣ 검색 결과 저장 ---
    retrieved_docs = []
    for doc in results:
        if isinstance(doc, Document):
            retrieved_docs.append({
                "page_content": doc.page_content,
                "metadata": doc.metadata
            })

    state["retrieved_docs"] = retrieved_docs
    state["message"] = f"{len(retrieved_docs)}개의 문서를 검색했습니다."
    return state
