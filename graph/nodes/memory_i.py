'''
=================================================================================
구현된 기능 (Phase 1)
=================================================================================

1. Write Memory (기록)
   - 이번 턴의 대화에서 "뭐가 다음에 다시 쓸만한가?" 판단
   - facts (사실): "당뇨병 진단", "HbA1c 7.2%", "환자명: 홍길동"
   - LLM으로 facts 추출 → 2-3줄 요약과 함께 저장

2. Read Memory (조회)
   - 다음 턴 시작 시 관련 대화 + facts 불러오기
   - 최근 N개 대화 우선 (기본 5개)
   - 조회된 대화의 access_count 자동 증가 (중요도 추적)
   - state["conversation_history"]에 저장하여 generate_answer에서 활용

3. Transform Memory (요약·정리) - 구현됨 ✅
   - 30일 이상 & access_count=0 → 삭제
   - 압축 없이 유지/삭제만 (간단하고 효율적)
   - 20턴마다 자동 실행

=============================================================================
데이터베이스 스키마
=================================================================================

테이블 1: conversation_memory
- id: INTEGER PRIMARY KEY AUTOINCREMENT
- timestamp: TEXT (ISO 8601 형식)
- original_question: TEXT (사용자의 원래 질문)
- user_question: TEXT (그래프 상에서 사용된 질문 - 하위 호환용)
- rewritten_question: TEXT (rewrite/context_rewrite 이후 질문)
- assistant_answer: TEXT (원본 답변)
- summary: TEXT (2-3줄 요약)
- facts: TEXT (JSON 배열 - 사실들)
- is_medical: BOOLEAN (의학 관련 여부)
- category: TEXT (질문 카테고리, JSON 배열)
- access_count: INTEGER (참조 횟수, 기본값 0)

테이블 2: metadata
- key: TEXT PRIMARY KEY
- value: TEXT

=================================================================================
주요 함수
=================================================================================

1. memory(state) - 통합 엔트리 포인트
   - final_answer 유무로 READ/WRITE 자동 판단

2. _read_memory(state, limit=5) - 조회
   - 최근 N개 대화 + facts 불러오기
   - access_count 자동 증가

3. _write_memory(state) - 저장
   - 대화 요약 + facts 추출하여 저장

4. _extract_summary_and_info(question, answer) - LLM 추출
   - GPT-4o mini 사용
   - 2-3줄 요약 + facts추출

5. _transform_memory() - 주기적 정리
   - 30일 이상 & access_count=0 대화 삭제

6. _increment_turn_count() - 턴 카운터 관리
   - metadata 테이블에 저장
'''


import sqlite3
from datetime import datetime
from openai import OpenAI
from graph.state import SelfRAGState
import json
import os

# OpenAI 클라이언트 초기화
client = OpenAI()

# DB 파일 경로 설정 (graph/memory/memory.db)
MEMORY_DIR = os.path.join(os.path.dirname(__file__), '..', 'memory')
DB_PATH = os.path.join(MEMORY_DIR, 'memory.db')

# memory 디렉토리가 없으면 생성
os.makedirs(MEMORY_DIR, exist_ok=True)


def init_memory_db():
    """
    메모리 데이터베이스 초기화
    테이블이 없으면 생성
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # conversation_memory 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            original_question TEXT,
            user_question TEXT NOT NULL,
            rewritten_question TEXT,
            assistant_answer TEXT NOT NULL,
            summary TEXT NOT NULL,
            facts TEXT,
            is_medical BOOLEAN NOT NULL,
            category TEXT,
            access_count INTEGER DEFAULT 0
        )
    ''')

    # metadata 테이블 (턴 카운터 등)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    # 기존 테이블에 original_question 컬럼 추가 (마이그레이션)
    try:
        cursor.execute('ALTER TABLE conversation_memory ADD COLUMN original_question TEXT')
        print("• [Memory] Added original_question column to existing table")
    except sqlite3.OperationalError:
        # 컬럼이 이미 존재하면 무시
        pass

    # 기존 테이블에 rewritten_question 컬럼 추가 (마이그레이션)
    try:
        cursor.execute('ALTER TABLE conversation_memory ADD COLUMN rewritten_question TEXT')
        print("• [Memory] Added rewritten_question column to existing table")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()
    print("• [Memory] Database initialized")


def _extract_summary_and_info(question: str, answer: str) -> dict:
    """
    LLM을 사용하여 대화에서 요약과 구조화된 정보 추출
    GPT-4o mini 사용

    Args:
        question: 사용자 질문
        answer: 시스템 답변

    Returns:
        dict: {
            "summary": "2-3줄 요약",
            "facts": ["사실1", "사실2", ...],
        }
    """
    try:
        prompt = f"""다음 대화를 분석하여 JSON 형식으로 출력하세요.

질문: {question}

답변: {answer}

다음 정보를 추출하세요:
1. summary: 대화를 2-3줄로 간결하게 요약 (질문 의도 + 답변 핵심만)
   - 사용자가 자신의 이름, 나이, 특징, 취미, 성격 등을 언급하면 반드시 요약에 포함하세요
   - 예: "사용자(홍길동)가 당뇨병에 대해 질문함"

2. facts: 사용자와 관련된 사실 정보를 추출
   - 사용자 정보: 이름, 나이, 성별, 직업, 취미, 특징 등
   - 의학 정보: 진단명, 수치, 날짜, 증상 등
   - 예: ["이름: 홍길동", "당뇨병 진단", "HbA1c 7.2%"]

출력 형식 (JSON):
{{
  "summary": "요약 내용",
  "facts": ["사실1", "사실2"],
}}

정보가 없는 항목은 빈 배열([])로 출력하세요.
출처 정보는 제외하세요."""

        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        result = json.loads(res.choices[0].message.content.strip())

        # 기본값 설정
        return {
            "summary": result.get("summary", ""),
            "facts": result.get("facts", []),
        }

    except Exception as e:
        print(f"• [Memory] Extraction failed: {e}")
        # 실패 시 기본 요약만 생성
        answer_preview = answer[:200] + "..." if len(answer) > 200 else answer
        return {
            "summary": f"질문: {question}\n답변: {answer_preview}",
            "facts": [],
        }


def _read_memory(state: SelfRAGState, limit: int = 5) -> SelfRAGState:
    """
    내부 함수: 메모리 읽기
    SQLite에서 최근 대화 요약 + facts를 읽어와서 state에 저장

    Args:
        state: 현재 상태
        limit: 불러올 대화 개수 (기본 5개)

    Returns:
        SelfRAGState: conversation_history가 업데이트된 상태
    """
    print("• [Memory] Reading from DB...")

    try:
        # DB 초기화 (테이블이 없으면 생성)
        init_memory_db()

        # SQLite에서 최근 N개 대화 조회
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # DB에 저장된 총 대화 개수 확인 (의학/비의학 모두)
        cursor.execute('''
            SELECT COUNT(*) FROM conversation_memory
        ''')
        total_count = cursor.fetchone()[0]

        # 실제 불러올 개수 결정 (DB에 저장된 개수와 limit 중 작은 값)
        actual_limit = min(limit, total_count)

        if actual_limit > 0:
            cursor.execute('''
                SELECT id, user_question, assistant_answer, summary, facts, timestamp
                FROM conversation_memory
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (actual_limit,))
            rows = cursor.fetchall()
        else:
            rows = []

        # 조회한 대화들의 access_count 증가
        if rows:
            ids = [row[0] for row in rows]
            placeholders = ','.join('?' * len(ids))
            cursor.execute(f'''
                UPDATE conversation_memory
                SET access_count = access_count + 1
                WHERE id IN ({placeholders})
            ''', ids)
            conn.commit()

        conn.close()

        if rows:
            # 요약들을 시간 순서대로 정렬 (오래된 것부터)
            # rows는 DESC로 조회했으므로 reversed로 뒤집으면 오래된 것부터 최신순
            rows = list(reversed(rows))

            # 직전 대화와 전체 대화 분리
            last_conversation = None
            summaries = []
            last_facts = []  # 직전 대화의 facts만 (신상정보용)
            all_facts = []   # 전체 facts (의학 정보 포함)

            for idx, (_, user_q, _, summary, facts_json, _) in enumerate(rows, 1):
                # 마지막(최신) 대화를 별도로 저장
                if idx == len(rows):
                    last_conversation = summary
                    # 직전 대화의 facts만 별도로 저장 (신상정보용)
                    if facts_json:
                        try:
                            last_facts = json.loads(facts_json)
                        except:
                            pass

                # 인덱스를 표시하여 순서를 명확히 함
                summaries.append(f"[대화 {idx}] {summary}")

                # 전체 facts 수집 (참고용)
                if facts_json:
                    try:
                        facts = json.loads(facts_json)
                        all_facts.extend(facts)
                    except:
                        pass

            summary_text = "\n\n".join(summaries)

            # state에 저장 (직전 대화와 전체 대화 분리)
            state["conversation_history"] = {
                "summary": summary_text,  # 전체 대화 요약 (최대 5개)
                "last_conversation": last_conversation or "",  # 직전 대화만
                "facts": last_facts,  # 직전 대화의 facts만 (신상정보)
                "all_facts": all_facts,  # 전체 facts (참고용)
                "count": str(len(summaries))
            }

            print(f"• [Memory] Loaded {len(summaries)}/{total_count} conversations (requested: {limit})")
            print(f"• [Memory] Last conversation facts: {len(last_facts)}, All facts: {len(all_facts)}")
            if last_conversation:
                print(f"• [Memory] Last conversation separated for priority reference")
        else:
            # 이전 대화가 없는 경우
            state["conversation_history"] = {
                "summary": "",
                "last_conversation": "",
                "facts": [],
                "all_facts": [],
                "count": "0"
            }
            print("• [Memory] No previous conversations found")

    except Exception as e:
        print(f"• [Memory] Read error: {e}")
        # 오류 시 빈 히스토리 설정
        state["conversation_history"] = {
            "summary": "",
            "last_conversation": "",
            "facts": [],
            "count": "0"
        }

    return state


def _write_memory(state: SelfRAGState) -> SelfRAGState:
    """
    내부 함수: 메모리 쓰기
    현재 대화를 요약하고 facts/preferences 추출하여 SQLite에 저장

    Args:
        state: 현재 상태 (질문과 답변 포함)

    Returns:
        SelfRAGState: 변경되지 않은 상태 (저장만 수행)
    """
    print("• [Memory] Writing to DB...")

    try:
        # 1. 의학 질문 여부 확인
        need_quit = state.get("need_quit", False)
        is_medical = not need_quit  # need_quit이 False면 의학 질문
        print(f"• [Memory] Debug: need_quit={need_quit}, is_medical={is_medical}")

        # 2. 답변 추출 (structured_answer 우선, 없으면 final_answer)
        structured_answer = state.get("structured_answer", {})
        if structured_answer and "answer" in structured_answer:
            assistant_answer = structured_answer["answer"]
            print(f"• [Memory] Debug: Using structured_answer")
        else:
            assistant_answer = state.get("final_answer", "")
            print(f"• [Memory] Debug: Using final_answer")
        
        print(f"• [Memory] Debug: assistant_answer length={len(assistant_answer) if assistant_answer else 0}")

        # 답변이 없으면 저장 안 함
        if not assistant_answer:
            print("• [Memory] Skip: no answer")
            return state

        # 실패 메시지는 저장 안 함 (의학 질문의 실패 케이스)
        skip_phrases = [
            "관련 정보를 찾을 수 없습니다",
            "관련 문서를 찾을 수 없습니다"
        ]

        if any(phrase in assistant_answer for phrase in skip_phrases):
            print("• [Memory] Skip: error message")
            return state

        # 3. 저장할 데이터 준비
        original_question = state.get("original_question", "")  # 원본 질문
        user_question = state.get("question", "")  # 그래프 내에서 사용된 질문 (호환용)
        rewritten_question = state.get("rewritten_question") or user_question  # 재작성된 질문

        # 출처 정보 제거한 답변 (요약용)
        answer_for_summary = assistant_answer.split("📚")[0].strip()

        # 4. LLM으로 요약 + facts 추출 (원본 질문 기준)
        extracted = _extract_summary_and_info(original_question or user_question, answer_for_summary)

        summary = extracted["summary"]
        facts = extracted["facts"]
        
        print(f"• [Memory] Debug: facts={facts}")
        print(f"• [Memory] Debug: summary={summary[:100]}...")
        
        # 저장 조건 확인:
        # 1. 의학 질문이면 무조건 저장 (일반적인 의학 지식 질문 포함)
        # 2. 비의학 질문이면 신상정보가 있을 때만 저장
        if not is_medical and (not facts or len(facts) == 0):
            print("• [Memory] Skip: non-medical question with no personal info")
            return state

        print("• [Memory] Debug: Proceeding to save...")

        # 5. SQLite에 저장
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        timestamp = datetime.now().isoformat()
        category = json.dumps(state.get("category", []))
        facts_json = json.dumps(facts, ensure_ascii=False)

        cursor.execute('''
            INSERT INTO conversation_memory
            (timestamp, original_question, user_question, rewritten_question, assistant_answer, summary, facts, is_medical, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, original_question, user_question, rewritten_question, assistant_answer, summary, facts_json, is_medical, category))

        conn.commit()
        
        # 10개 초과 시 오래된 데이터 정리
        cursor.execute('SELECT COUNT(*) FROM conversation_memory')
        count = cursor.fetchone()[0]
        
        if count > 10:
            cursor.execute('''
                DELETE FROM conversation_memory 
                WHERE id NOT IN (
                    SELECT id FROM conversation_memory 
                    ORDER BY timestamp DESC 
                    LIMIT 10
                )
            ''')
            deleted_count = count - 10
            conn.commit()
            print(f"• [Memory] Cleaned up {deleted_count} old records (kept latest 10)")
        
        conn.close()

        print(f"• [Memory] ✅ Successfully saved: summary + {len(facts)} facts")

    except Exception as e:
        print(f"• [Memory] Write error: {e}")
        # 오류가 발생해도 state는 그대로 반환 (답변 전달은 계속됨)

    return state


def _increment_turn_count() -> int:
    """
    턴 카운터 증가 및 반환
    metadata 테이블에 저장

    Returns:
        int: 현재 턴 카운트
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 현재 카운트 조회
    cursor.execute('SELECT value FROM metadata WHERE key = "turn_count"')
    row = cursor.fetchone()
    current_count = int(row[0]) if row else 0

    # 카운트 증가
    new_count = current_count + 1
    cursor.execute('''
        INSERT OR REPLACE INTO metadata (key, value)
        VALUES ("turn_count", ?)
    ''', (str(new_count),))

    conn.commit()
    conn.close()

    return new_count


def _transform_memory():
    """
    주기적 메모리 정리
    30일 이상 & access_count=0 인 대화 삭제
    """
    print("• [Memory Transform] Starting cleanup...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 30일 이상 & access_count=0 인 대화 삭제
    cursor.execute('''
        DELETE FROM conversation_memory
        WHERE datetime(timestamp) < datetime('now', '-30 days')
        AND access_count = 0
    ''')

    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()

    print(f"• [Memory Transform] Deleted {deleted_count} old unused conversations")


# Transform 실행 간격 (턴 수)
TRANSFORM_INTERVAL = 20


def memory_read(state: SelfRAGState, limit: int = 5) -> SelfRAGState:
    """
    메모리 읽기 노드
    대화 시작 시 이전 대화를 불러와서 conversation_history에 저장

    Args:
        state: 현재 상태
        limit: 불러올 대화 개수 (기본 5개)

    Returns:
        SelfRAGState: conversation_history가 업데이트된 상태
    """
    print("• [Memory Read] start")
    state = _read_memory(state, limit)
    print("• [Memory Read] complete")
    return state


def memory_write(state: SelfRAGState) -> SelfRAGState:
    """
    메모리 쓰기 노드
    대화 종료 시 현재 대화를 저장하고 주기적으로 정리 실행

    Args:
        state: 현재 상태

    Returns:
        SelfRAGState: 변경되지 않은 상태 (저장만 수행)
    """
    print("🔥 [Memory Write] ===== FUNCTION CALLED =====")
    print(f"🔥 [Memory Write] State keys: {list(state.keys())}")
    print(f"🔥 [Memory Write] final_answer exists: {'final_answer' in state}")
    print(f"🔥 [Memory Write] structured_answer exists: {'structured_answer' in state}")
    
    state = _write_memory(state)

    # 턴 카운터 증가 및 주기적 정리
    turn_count = _increment_turn_count()
    if turn_count % TRANSFORM_INTERVAL == 0:
        _transform_memory()

    print("• [Memory Write] complete")
    return state


# 하위 호환성을 위한 통합 함수 (deprecated)
def memory(state: SelfRAGState, limit: int = 5) -> SelfRAGState:
    """
    통합 메모리 노드 (deprecated - 하위 호환성용)
    memory_read와 memory_write로 분리 권장

    Args:
        state: 현재 상태
        limit: READ 시 불러올 대화 개수 (기본 5개)

    Returns:
        SelfRAGState: 업데이트된 상태
    """
    print("• [Memory] start (deprecated - use memory_read/memory_write)")

    # structured_answer 존재 여부로 READ/WRITE 모드 판단
    structured_answer = state.get("structured_answer", {})

    if structured_answer:
        # WRITE 모드
        state = memory_write(state)
    else:
        # READ 모드
        state = memory_read(state, limit)

    print("• [Memory] complete")
    return state

