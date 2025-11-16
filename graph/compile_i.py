from langgraph.graph import StateGraph, END

# 노드 함수 import
from graph.state_i import SelfRAGState
from graph.nodes.classifier_i import classifier
from graph.nodes.medical_check import medical_check
from graph.nodes.web_search import web_search
from graph.nodes.retrieval import retrieval
from graph.nodes.evaluate_chunk_i import evaluate_chunk
from graph.nodes.rewrite_query_i import rewrite_query
from graph.nodes.generate_answer_i import generate_answer
from graph.nodes.memory_i import memory_read, memory_write

def create_medical_rag_workflow():
    """
    의료 RAG 워크플로우 생성 (개선 버전)
    conversation_type 기반 라우팅
    """
    workflow = StateGraph(SelfRAGState)

    def route_by_conversation_type(state: SelfRAGState) -> str:
        """
        conversation_type에 따라 분기
        - "user_info": generate_answer로 (원본 질문과 conversation_history 전달)
        - "non_medical": END로 (안내 메시지 출력 후 바로 종료)
        - "medical": medical_check로 (기존 RAG 파이프라인)
        """
        conv_type = state.get("conversation_type", "medical")

        if conv_type == "user_info":
            return "generate_answer"
        elif conv_type == "non_medical":
            return END
        else:  # medical
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
    workflow.add_node("memory_read", memory_read)
    workflow.add_node("classifier", classifier)
    workflow.add_node("medical_check", medical_check)
    workflow.add_node("web_search", web_search)
    workflow.add_node("retrieval", retrieval)
    workflow.add_node("evaluate_chunk", evaluate_chunk)
    workflow.add_node("rewrite_query", rewrite_query)
    workflow.add_node("generate_answer", generate_answer)
    workflow.add_node("memory_write", memory_write)

    # --- 시작점 설정 ---
    workflow.set_entry_point("memory_read")

    # --- 엣지 정의 ---

    # 0. Memory Read → Classifier (일반 엣지)
    workflow.add_edge("memory_read", "classifier")

    # 1. Classifier 다음 경로 (조건부 엣지)
    # - conversation_type에 따라 분기
    #   - "user_info": generate_answer로 (원본 질문과 conversation_history 전달)
    #   - "non_medical": END로 (안내 메시지 출력 후 바로 종료)
    #   - "medical": medical_check로 (기존 RAG 파이프라인)
    workflow.add_conditional_edges(
        "classifier",
        route_by_conversation_type,
        {
            "generate_answer": "generate_answer",
            "medical_check": "medical_check",
            END: END
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

    # 7. Generate Answer → Memory Write → END (일반 엣지)
    workflow.add_edge("generate_answer", "memory_write")

    # 8. Memory Write → END (일반 엣지)
    workflow.add_edge("memory_write", END)

    # --- 그래프 컴파일 ---
    app = workflow.compile()
    return app
