# graph/workflow.py (또는 네가 쓰는 의료 workflow 파일)
from langgraph.graph import StateGraph, END

from graph.state import SelfRAGState
from graph.nodes.classifier import classifier
from graph.nodes.medical_check import medical_check
from graph.nodes.web_search import web_search
from graph.nodes.retrieval import retrieval
from graph.nodes.evaluate_chunk import evaluate_chunk
from graph.nodes.rewrite_query import rewrite_query
from graph.nodes.generate_answer import generate_answer
from graph.nodes.memory_node import memory_node

#from rag.queries.memory_repository import init_memory_db


def create_medical_rag_workflow():
    """
    의료 RAG 워크플로우 생성
    - classifier 이후: memory 노드 (질문 재작성)
    - generate_answer 이후: memory 노드 (질문/답변 요약 저장)
    """

    # SQLite memory 초기화 (앱 시작 시 1번만 호출해도 됨)
    #init_memory_db()

    workflow = StateGraph(SelfRAGState)

    # --- 노드 등록 ---
    workflow.add_node("classifier", classifier)
    workflow.add_node("medical_check", medical_check)
    workflow.add_node("web_search", web_search)
    workflow.add_node("retrieval", retrieval)
    workflow.add_node("evaluate_chunk", evaluate_chunk)
    workflow.add_node("rewrite_query", rewrite_query)
    workflow.add_node("generate_answer", generate_answer)
    workflow.add_node("memory", memory_node)

    # --- 시작점 ---
    workflow.set_entry_point("classifier")

    # --- 분기 함수 정의 ---

    # 1) classifier 이후 분기:
    # - need_quit=True → END
    # - 아니면 memory 로 (첫 번째 memory 호출)
    def branch_after_classifier(state: SelfRAGState) -> str:
        if state.get("need_quit", False):
            return "end"
        return "memory"

    workflow.add_conditional_edges(
        "classifier",
        branch_after_classifier,
        {
            "end": END,
            "memory": "memory",
        },
    )

    # 2) memory 이후 분기:
    # - final_answer 유무에 따라 경로 결정
    #   - final_answer 없음 → medical_check (첫 번째 호출 후 흐름)
    #   - final_answer 있음 → END (두 번째 호출 후 종료)
    def branch_after_memory(state: SelfRAGState) -> str:
        if state.get("final_answer"):
            return "end"
        return "medical_check"

    workflow.add_conditional_edges(
        "memory",
        branch_after_memory,
        {
            "end": END,
            "medical_check": "medical_check",
        },
    )

    # 3) medical_check 이후 분기:
    # - is_terminology=True → web_search
    # - False → retrieval
    workflow.add_conditional_edges(
        "medical_check",
        lambda s: "terminology" if s.get("is_terminology") else "general",
        {
            "terminology": "web_search",
            "general": "retrieval",
        },
    )

    # 4) web_search → generate_answer
    workflow.add_edge("web_search", "generate_answer")

    # 5) retrieval → evaluate_chunk
    workflow.add_edge("retrieval", "evaluate_chunk")

    # 6) evaluate_chunk 이후 분기:
    def branch_after_evaluate(state: SelfRAGState) -> str:
        # 관련성이 충분하면 바로 답변
        if state.get("is_relevant", False):
            return "generate_answer"

        # 이미 재작성 한 번 했으면 더는 재작성 안 함
        if state.get("rewrite_count", 0) >= 1:
            return "generate_answer"

        return "rewrite_query"

    workflow.add_conditional_edges(
        "evaluate_chunk",
        branch_after_evaluate,
        {
            "generate_answer": "generate_answer",
            "rewrite_query": "rewrite_query",
        },
    )

    # 7) rewrite_query → retrieval (루프)
    workflow.add_edge("rewrite_query", "retrieval")

    # 8) generate_answer → memory (두 번째 memory 호출)
    workflow.add_edge("generate_answer", "memory")

    # 그래프 컴파일
    app = workflow.compile()
    return app
