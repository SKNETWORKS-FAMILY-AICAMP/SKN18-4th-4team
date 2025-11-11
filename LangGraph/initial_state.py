from typing import List, Dict, Any, TypedDict, Tuple


class SelfRAGState(TypedDict):
    """Self-RAG 시스템의 전체 상태 정의"""

    # 입력
    question: str                    # 사용자 질문

    # 검색 관련
    need_quit: bool                  # 검색 종료 여부 플래그
    domain: str                      # 상위 분류 (예: 고객지원 / 기술지원)
    category: List[str]              # 세부 카테고리 목록
    max_token: bool                  # 토큰 초과 여부

    # 답변 생성 관련
    retrieval_question: bool         # 검색용 질문 여부
    search_queries: Dict[str, List[Tuple[Any, float]]]  # 검색 질의 결과 (query, score)
    retrieved_docs: List[Dict[str, Any]]                # 평가 이후의 유효 문서 목록
    context: str                     # 프롬프트에 삽입될 최종 문맥

    # 평가 관련
    relevance_score: float           # 문서 관련성 점수
    message: str                     # LLM 또는 시스템 메시지

    # 최종 결과
    final_answer: str                # 최종 답변 (출처 포함 가능)

    # 대화 이력
    conversation_history: Dict[str, str]  # 이전 대화 메시지 기록


print("✅ SelfRAGState 정의 완료")
