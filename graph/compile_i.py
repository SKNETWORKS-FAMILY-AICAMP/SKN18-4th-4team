"""
메모리 기능이 통합된 의료 RAG 워크플로우
classifier → memory (READ) → medical_check → ... → generate_answer → memory (WRITE) → END
conversation_history는 state를 통해 각 노드에 전달되어 시스템 메시지에 활용됨
"""
from langgraph.graph import StateGraph, END

# 노드 함수 import
from graph.state import SelfRAGState
from graph.nodes.classifier import classifier
from graph.nodes.memory_i import memory_read, memory_write
from graph.nodes.medical_check import medical_check
from graph.nodes.web_search import web_search
from graph.nodes.retrieval import retrieval
from graph.nodes.evaluate_chunk import evaluate_chunk
from graph.nodes.rewrite_query import rewrite_query
from graph.nodes.generate_answer_i import generate_answer_i

import sys
import os

# 주피터 노트북/Colab 등에서 'graph' 모듈 인식을 돕기 위한 경로 추가
import sys
import os

try:
    # __file__이 존재하지 않을 수 있으니 예외처리
    current_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    # 주피터 환경: __file__ 미정의 → 현재 작업 디렉토리 사용
    current_dir = os.getcwd()

parent_dir = os.path.abspath(os.path.join(current_dir, ".."))

if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
# (노트: graph/ 하위에서 import graph.XX 시, 상위 디렉토리를 sys.path에 추가해야 ModuleNotFoundError 방지)



def create_medical_rag_workflow():
    """
    메모리 기능이 통합된 의료 RAG 워크플로우 생성

    워크플로우 흐름:
    1. classifier: 의학 관련 질문 판별
    2. memory (READ 모드): 이전 대화 불러오기 → conversation_history에 저장
    3. medical_check: 용어 질문 vs 일반 질문 분류
    4. web_search OR retrieval: 정보 검색
    5. evaluate_chunk: 검색 결과 평가 (retrieval 경로만)
    6. rewrite_query: 질문 재작성 (필요시)
    7. generate_answer: 답변 생성 (conversation_history 활용)
    8. memory (WRITE 모드): 대화 저장 + 20턴마다 정리
    """
    workflow = StateGraph(SelfRAGState)

    def evaluate_relevance(state: SelfRAGState) -> str:
        """검색된 문서의 관련성 평가 후 분기"""
        if state.get("is_relevant", False):
            return "generate_answer"
        # 이미 한 번 재작성했으면 더 이상 재작성하지 않고 답변 생성
        if state.get("rewrite_count", 0) >= 1:
            return "generate_answer"
        return "rewrite_query"

    def after_generate_answer(state: SelfRAGState) -> str:
        """Generate Answer 후 분기: 답변이 있으면 memory_write, 없으면 바로 END"""
        # final_answer 또는 structured_answer가 있으면 메모리에 저장 (의학/비의학 모두)
        final_answer = state.get("final_answer")
        structured_answer = state.get("structured_answer", {})
        
        print(f"🔥 [Workflow] after_generate_answer: final_answer={bool(final_answer)}, structured_answer={bool(structured_answer)}")
        
        if final_answer or (structured_answer and structured_answer.get("answer")):
            print("🔥 [Workflow] → Going to memory_write")
            return "memory_write"
        
        print("🔥 [Workflow] → Going to END (no answer)")
        return END  # 답변 생성 실패 시 바로 종료

    # --- 노드 등록 ---
    workflow.add_node("classifier", classifier)
    workflow.add_node("memory_read", memory_read)  # 메모리 읽기 노드
    workflow.add_node("memory_write", memory_write)  # 메모리 쓰기 노드
    workflow.add_node("medical_check", medical_check)
    workflow.add_node("web_search", web_search)
    workflow.add_node("retrieval", retrieval)
    workflow.add_node("evaluate_chunk", evaluate_chunk)
    workflow.add_node("rewrite_query", rewrite_query)
    workflow.add_node("generate_answer", generate_answer_i)

    # --- 시작점 설정 ---
    workflow.set_entry_point("classifier")

    # --- 엣지 정의 ---

    # 1. Classifier → Memory Read (일반 엣지)
    # 모든 질문(의학/비의학)이 메모리를 먼저 읽음
    workflow.add_edge("classifier", "memory_read")

    # 2. Memory Read 다음 경로 (조건부 엣지)
    # - need_quit이 True면 END로 (비의학 질문은 바로 종료)
    # - need_quit이 False면 medical_check로 (의학 질문 처리)
    def after_memory_read(state: SelfRAGState) -> str:
        """Memory Read 다음 경로 결정"""
        if state.get("need_quit", False):
            # 비의학 질문 → 안내 메시지 설정 후 바로 END
            state["final_answer"] = "의학과 관련된 질문이 아닙니다. 의학과 관련된 질문을 주세요."
            print("\n" + "=" * 60)
            print(" 답변")
            print("=" * 60)
            print("의학과 관련된 질문이 아닙니다. 의학과 관련된 질문을 주세요.")
            print("=" * 60)
            print("🔥 [Workflow] Non-medical question → Going to END")
            return END
        return "medical_check"  # 의학 질문 → 의학 검사

    workflow.add_conditional_edges(
        "memory_read",
        after_memory_read,
        {
            END: END,
            "medical_check": "medical_check"
        }
    )

    # 3. Memory Write → END (일반 엣지)
    workflow.add_edge("memory_write", END)

    # 3. Medical Check 다음 경로 (조건부 엣지)
    # - is_terminology가 True면 web_search로, False면 retrieval로
    workflow.add_conditional_edges(
        "medical_check",
        lambda state: "terminology" if state.get("is_terminology") else "general",
        {
            "terminology": "web_search",
            "general": "retrieval",
        }
    )

    # 5. Web Search → Generate Answer
    workflow.add_edge("web_search", "generate_answer")

    # 6. Retrieval → Evaluate Chunk
    workflow.add_edge("retrieval", "evaluate_chunk")

    # 7. Evaluate Chunk 다음 경로 (조건부 엣지)
    # - is_relevant가 True면 generate_answer로, False면 rewrite_query로
    workflow.add_conditional_edges(
        "evaluate_chunk",
        evaluate_relevance,
        {
            "generate_answer": "generate_answer",
            "rewrite_query": "rewrite_query"
        }
    )

    # 8. Rewrite Query → Retrieval (순환)
    workflow.add_edge("rewrite_query", "retrieval")

    # 9. Generate Answer → Memory Write 또는 END
    workflow.add_conditional_edges(
        "generate_answer",
        after_generate_answer,
        {
            "memory_write": "memory_write",
            END: END
        }
    )

    # --- 그래프 컴파일 ---
    # recursion_limit 설정: 최대 50회까지 재시도 허용
    app = workflow.compile()
    return app
