from langgraph.graph import StateGraph, END

# 노드 함수 import
from graph.state import SelfRAGState
from graph.nodes.classifier import classifier
from graph.nodes.medical_check import medical_check
from graph.nodes.web_search import web_search
from graph.nodes.retrieval import retrieval
from graph.nodes.evaluate_chunk import evaluate_chunk
from graph.nodes.rewrite_query import rewrite_query
from graph.nodes.generate_answer import generate_answer

def create_medical_rag_workflow():
    """
    의료 RAG 워크플로우 생성
    retrieval 노드는 내부적으로 VectorRetriever를 사용하여 DB에 접근
    """
    workflow = StateGraph(SelfRAGState)

    def classify_quit(state: SelfRAGState) -> str:
        """의학 관련 질문인지 판별 후 분기"""
        if state.get("need_quit", False):
            return END
        return "medical_check"

    def evaluate_relevance(state: SelfRAGState) -> str:
        """검색된 문서의 관련성 평가 후 분기"""
        if state.get("is_relevant", False):
            return "generate_answer"
        # rewrite 후에도 관련성 있는 chunk를 찾지 못한 경우 END로 이동
        if state.get("rewrite_count", 0) >= 1:
            # is_relevant가 False면 (관련성이 낮으면) END로 이동
            return END
        return "rewrite_query"

    # --- 노드 등록 ---
    workflow.add_node("classifier", classifier)
    workflow.add_node("medical_check", medical_check)
    workflow.add_node("web_search", web_search)
    workflow.add_node("retrieval", retrieval)
    workflow.add_node("evaluate_chunk", evaluate_chunk)
    workflow.add_node("rewrite_query", rewrite_query)
    workflow.add_node("generate_answer", generate_answer)

    # --- 시작점 설정 ---
    workflow.set_entry_point("classifier")

    # --- 엣지 정의 ---

    # 1. Classifier 다음 경로 (조건부 엣지)
    # - need_quit이 True면 END, False면 medical_check로
    workflow.add_conditional_edges(
        "classifier",
        classify_quit,
        {
            END: END,
            "medical_check": "medical_check"
        }
    )

    # 2. Medical Check 다음 경로 (조건부 엣지)
    # - is_terminology가 True면 web_search로, False면 retrieval로
    workflow.add_conditional_edges(
        "medical_check",
        lambda state: "terminology" if state.get("is_terminology") else "general",
        {
            "terminology": "web_search",
            "general": "retrieval",
        }
    )

    # 3. Web Search → Generate Answer → END (일반 엣지)
    workflow.add_edge("web_search", "generate_answer")

    # 4. Retrieval → Evaluate Chunk (일반 엣지)
    workflow.add_edge("retrieval", "evaluate_chunk")

    # 5. Evaluate Chunk 다음 경로 (조건부 엣지)
    # - is_relevant가 True면 generate_answer로
    # - rewrite 후 chunk가 없으면 END로
    # - 그 외에는 rewrite_query로
    workflow.add_conditional_edges(
        "evaluate_chunk",
        evaluate_relevance,
        {
            "generate_answer": "generate_answer",
            "rewrite_query": "rewrite_query",
            END: END
        }
    )

    # 6. Rewrite Query → Retrieval (순환) (일반 엣지)
    workflow.add_edge("rewrite_query", "retrieval")

    # 7. Generate Answer → END (일반 엣지)
    workflow.add_edge("generate_answer", END)

    # --- 그래프 컴파일 ---
    app = workflow.compile()
    return app