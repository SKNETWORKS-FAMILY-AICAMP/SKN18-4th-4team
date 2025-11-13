from typing import List, Dict, Any, TypedDict, Tuple


class SelfRAGState(TypedDict):
    """Self-RAG 시스템의 상태를 정의하는 클래스"""
    
    # 입력 정보
    question: str  # 사용자 질문
    
    # 검색 관련
    need_quit: bool  # 검색 필요 여부
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
    final_answer: str  # 최종 답변 (출처 포함)

    # 대화 이력
    conversation_history: Dict[str, str]  # 이전 대화 메시지 리스트
    


print("SelfRAGState 클래스 정의 완료!")