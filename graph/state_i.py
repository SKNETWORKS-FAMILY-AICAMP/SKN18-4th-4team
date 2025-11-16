from typing import List, Dict, Any, TypedDict, Tuple, Literal


class SelfRAGState(TypedDict):
    """Self-RAG 시스템의 상태를 정의하는 클래스"""

    # 입력 정보
    question: str  # 사용자 질문

    # 대화 분류 (통합 필드)
    conversation_type: Literal["medical", "user_info", "non_medical"]  # 대화 유형 (medical/user_info/non_medical)
    original_question: str  # 첫 번째 입력 질문 (대화 기준점)
    is_follow_up: bool  # 직전 대화의 후속 질문 여부

    # 검색 관련
    is_terminology: bool  # 의학 용어 질문 여부
    category: List[str]  # 세부 카테고리
    max_token:bool

    # 답변 생성 관련
    retrieval_question:bool
    search_queries: Dict[str, List[Tuple[Any, float]]] # RAG 결과
    retrieved_docs: List[Dict[str, Any]] # 검증이후 query
    context: str # LLM Templete에 들어갈 문장 구성
    sources: List[str]  # 출처 정보
    #chunk_metadata: Dict[str,List[Dict[str]]]

    # 평가 관련
    is_relevant: bool  # 문서 관련성 평가 결과
    relevance_score: float  # 관련성 점수
    message:str
    rewrite_count: int  # 쿼리 재작성 횟수

    # 최종 결과
    final_answer: str  # 최종 답변 (출처 포함) - 평문용
    structured_answer: Dict[str, Any]  # JSON 구조화된 답변
    llm_score: float  # LLM 자체 신뢰도 점수 (0.0-1.0)

    # 대화 이력
    # 최신 5개 대화 유지. 형식: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]
    # 순서: 최신 → 오래된 (가장 최근 대화가 0번째, 가장 최근 이름 우선)
    conversation_history: List[Dict[str, str]]
    


print("SelfRAGState 클래스 정의 완료!")