# nodes/generate_answer.py
import json
import re
from openai import OpenAI
from graph.state import SelfRAGState

client = OpenAI()


def extract_used_citation_numbers(answer: str) -> set:
    """답변에서 사용된 출처 번호([1], [2] 등)를 추출"""
    pattern = r'\[(\d+)\]'
    matches = re.findall(pattern, answer)
    return set(int(num) for num in matches)


def remove_citation_numbers(answer: str) -> str:
    """답변에서 출처 번호 [1], [2] 등을 제거"""
    return re.sub(r'\[\d+\]', '', answer)


def filter_and_renumber_sources(answer: str, sources: list) -> tuple:
    """
    답변에서 사용된 출처만 필터링하고 번호 재매핑
    Returns: (renumbered_answer, filtered_sources)
    """
    # 사용된 출처 번호 추출
    used_numbers = extract_used_citation_numbers(answer)

    # 번호 매핑 생성 (원본 번호 -> 새 번호)
    number_mapping = {}
    filtered_sources = []

    for new_num, old_num in enumerate(sorted(used_numbers), start=1):
        if 1 <= old_num <= len(sources):
            number_mapping[old_num] = new_num
            source = sources[old_num - 1]

            # 출처 텍스트 추출
            if isinstance(source, str):
                source_text = source
            else:
                # 딕셔너리인 경우 title 추출
                source_dict = dict(source) if isinstance(source, dict) else {"title": str(source)}
                source_text = source_dict.get("title", str(source))

            # "[번호] 출처" 형식으로 저장
            filtered_sources.append(f"[{new_num}] {source_text}")

    # 답변의 출처 번호를 재번호화
    renumbered_answer = answer
    # 모든 사용된 번호에 대해 처리 (유효하지 않은 번호도 제거)
    for old_num in sorted(used_numbers, reverse=True):
        if old_num in number_mapping:
            new_num = number_mapping[old_num]
            renumbered_answer = renumbered_answer.replace(f'[{old_num}]', f'[{new_num}]')
        else:
            # 유효하지 않은 번호는 제거
            renumbered_answer = renumbered_answer.replace(f'[{old_num}]', '')

    return renumbered_answer, filtered_sources


def calculate_llm_score(answer: str, context: str, relevance_score: float) -> float:
    """
    LLM 신뢰도 점수 계산
    - 관련성 점수 기반
    - 답변 길이 평가 (너무 짧으면 감점)
    """
    # 기본 점수는 관련성 점수에서 시작
    base_score = relevance_score if relevance_score > 0 else 0.70

    # 답변 길이 평가 (너무 짧으면 감점)
    answer_length = len(answer)
    if answer_length < 50:
        length_penalty = 0.20
    elif answer_length < 100:
        length_penalty = 0.10
    else:
        length_penalty = 0.0

    # 최종 점수 계산
    final_score = base_score - length_penalty

    # 0.0 ~ 1.0 범위로 제한하고 소수점 2자리로 반올림
    return round(max(0.0, min(1.0, final_score)), 2)


def generate_answer(state: SelfRAGState) -> SelfRAGState:
    """
    통합 답변 생성 노드
    - 비의학 질문: 안내 메시지
    - 의학 용어 질문: WebSearch 결과 기반 답변
    - 일반 의학 질문: RAG 문서 기반 답변
    """

    # 시작 로그
    query = state.get("question", "")
    context_len = len(state.get("context", ""))
    is_terminology = state.get("is_terminology", False)
    print(f"• [Generate] start (context_chars={context_len}, is_terminology={is_terminology})")

    # 1. 비의학 질문 처리 (guidance 로직)
    if state.get("need_quit", False):
        state["final_answer"] = """
죄송합니다. 현재 시스템은 의학 관련 질문만 답변할 수 있습니다.

의학, 건강, 질병, 증상, 치료 등과 관련된 질문을 해주시면 도움을 드리겠습니다.

예시:
- "당뇨병이란 무엇인가요?"
- "고혈압의 증상은 무엇인가요?"
- "독감 예방접종은 언제 받는 것이 좋나요?"
        """.strip()
        return state

    # 2. 의학 질문 처리
    query = state.get("question", "")
    context = state.get("context", "")
    sources = state.get("sources", [])
    is_terminology = state.get("is_terminology", False)

    # 컨텍스트가 없는 경우
    if not context:
        if is_terminology:
            state["final_answer"] = "죄송합니다. 관련 정보를 찾을 수 없습니다."
        else:
            state["final_answer"] = "죄송합니다. 관련 문서를 찾을 수 없습니다."
        return state

    # 3. WebSearch 결과 기반 답변 (answer_websearch 로직)
    if is_terminology:
        prompt = f"""
사용자 질문: {query}

검색된 정보:
{context}

위 정보를 바탕으로 아래 형식에 맞춰 사용자 질문에 답변해주세요.

**답변 형식:**
[주요 내용]
핵심 개념이나 정의를 1-2문장으로 설명합니다.

[관련 상식 보충]
주요 내용과 관련된 추가 정보, 배경 지식, 또는 상세 설명을 제공합니다.

[답변 요약]
전체 내용을 1-2문장으로 간단히 요약합니다.

**출처 표기 규칙 (매우 중요!):**
- 반드시 [1], [2], [3] 형식으로 표기하세요 (쉼표와 띄어쓰기 포함)
- [1][2] 처럼 붙여쓰지 마세요 ❌
- (출처 1), (출처 2) 형식 사용 금지 ❌
- 예시: "당뇨병은 질환입니다[1], [2]." ✓

**작성 규칙:**
- 검색 결과에 있는 정보만 사용하세요
- 각 섹션 제목은 반드시 []로 감싸서 표시하세요
- [주요 내용], [관련 상식 보충], [답변 요약] 3개 섹션만 작성하세요
- [출처] 같은 추가 섹션 작성 금지
- 의학 정보는 신중하게 전달하세요
- 긴 문서들은 간단하게 요약하여 중요 정보들만 전달해주세요
- 핵심 단어에 ** markdown 강조 표현을 적용하세요
        """

        res = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[{"role": "user", "content": prompt}]
        )

        answer = res.choices[0].message.content.strip()

        # 답변 정제 및 출처 필터링
        answer_with_citations, filtered_sources = filter_and_renumber_sources(answer, sources)

        # LLM 신뢰도 점수 계산
        llm_score = calculate_llm_score(answer_with_citations, context, state.get("relevance_score", 0.0))

        # JSON 구조화된 답변 생성
        state["structured_answer"] = {
            "type": "external",
            "answer": answer_with_citations,
            "references": filtered_sources,  # 실제 사용된 출처만 포함
            "llm_score": llm_score,
            "relevance_score": round(state.get("relevance_score", 0.0), 2)
        }
        state["llm_score"] = llm_score

    # 4. RAG 문서 기반 답변 (answer_rag 로직)
    else:
        prompt = f"""
사용자 질문: {query}

관련 문서:
{context}

위 문서를 근거로 아래 형식에 맞춰 사용자 질문에 답변해주세요.

**답변 형식:**
[주요 내용]
핵심 개념이나 정의를 1-2문장으로 설명합니다.

[관련 상식 보충]
주요 내용과 관련된 추가 정보, 배경 지식, 또는 상세 설명을 제공합니다.

[답변 요약]
전체 내용을 1-2문장으로 간단히 요약합니다.

**출처 표기 규칙 (매우 중요!):**
- 반드시 [1], [2], [3] 형식으로 표기하세요 (쉼표와 띄어쓰기 포함)
- [1][2] 처럼 붙여쓰지 마세요 ❌
- (출처 1), (출처 2) 형식 사용 금지 ❌
- 예시: "당뇨병은 질환입니다[1], [2]." ✓

**작성 규칙:**
- 문서에 있는 정보만 사용하세요
- 각 섹션 제목은 반드시 []로 감싸서 표시하세요
- [주요 내용], [관련 상식 보충], [답변 요약] 3개 섹션만 작성하세요
- [출처] 같은 추가 섹션 작성 금지
- 의학 정보는 신중하고 정확하게 전달하세요
- 추측하지 말고 문서 내용에 충실하세요
- 핵심 단어에 ** markdown 강조 표현을 적용하세요
        """

        res = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[{"role": "user", "content": prompt}]
        )

        answer = res.choices[0].message.content.strip()

        # 답변 정제 및 출처 필터링
        answer_with_citations, filtered_sources = filter_and_renumber_sources(answer, sources)

        # LLM 신뢰도 점수 계산
        llm_score = calculate_llm_score(answer_with_citations, context, state.get("relevance_score", 0.0))

        # JSON 구조화된 답변 생성
        state["structured_answer"] = {
            "type": "internal",
            "answer": answer_with_citations,
            "references": filtered_sources,  # 실제 사용된 출처만 포함
            "llm_score": llm_score,
            "relevance_score": round(state.get("relevance_score", 0.0), 2)
        }
        state["llm_score"] = llm_score

    # 완료 로그
    answer_len = len(state.get("final_answer", ""))
    print(f"• [Generate] complete (answer_chars={answer_len})")

    return state
