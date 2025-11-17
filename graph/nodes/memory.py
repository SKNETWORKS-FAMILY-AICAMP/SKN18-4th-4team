import sqlite3
from datetime import datetime
from graph.state import SelfRAGState
from openai import OpenAI
import os

client = OpenAI()

# DB 파일 경로 설정 (graph/memory/memory.db)
MEMORY_DIR = os.path.join(os.path.dirname(__file__), '..', 'memory')
DB_PATH = os.path.join(MEMORY_DIR, 'memory.db')

# memory 디렉토리가 없으면 생성
os.makedirs(MEMORY_DIR, exist_ok=True)


def init_memory_db():
    """
    메모리 데이터베이스 초기화
    테이블이 없으면 생성, 스키마 마이그레이션 처리
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 기존 테이블 확인
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversation_memory'")
    table_exists = cursor.fetchone() is not None

    if table_exists:
        # 기존 테이블의 컬럼 확인
        cursor.execute("PRAGMA table_info(conversation_memory)")
        columns = [col[1] for col in cursor.fetchall()]

        # conversation_type 컬럼이 없으면 스키마 변경 필요 -> 테이블 재생성
        if 'conversation_type' not in columns:
            print("• [Memory] Old schema detected, migrating to new schema...")
            cursor.execute('DROP TABLE IF EXISTS conversation_memory')
            table_exists = False

    if table_exists:
        # question_summary, answer_summary 컬럼이 있는지 확인
        if 'question_summary' not in columns or 'answer_summary' not in columns:
            print("• [Memory] Adding summary columns to existing table...")
            # 새 컬럼 추가
            try:
                cursor.execute('ALTER TABLE conversation_memory ADD COLUMN question_summary TEXT')
                cursor.execute('ALTER TABLE conversation_memory ADD COLUMN answer_summary TEXT')
                print("• [Memory] Added summary columns")
            except sqlite3.OperationalError as e:
                print(f"• [Memory] Columns may already exist: {e}")

    if not table_exists:
        # conversation_memory 테이블 생성 (새 스키마)
        cursor.execute('''
            CREATE TABLE conversation_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                original_question TEXT NOT NULL,
                assistant_answer TEXT NOT NULL,
                question_summary TEXT,
                answer_summary TEXT,
                conversation_type TEXT NOT NULL
            )
        ''')
        print("• [Memory] Created new conversation_memory table with summary columns")

    # metadata 테이블 (턴 카운터 등)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    conn.commit()
    conn.close()
    print("• [Memory] Database initialized")


def _summarize_conversation(question: str, answer: str, conversation_type: str) -> dict:
    """
    대화를 1-2줄로 요약

    Args:
        question: 원본 질문
        answer: 원본 답변
        conversation_type: 대화 유형

    Returns:
        dict: {"question_summary": "...", "answer_summary": "..."}
    """
    try:
        # user_info 타입은 원문 그대로 (이름 등 중요 정보)
        if conversation_type == "user_info":
            print(f"• [Memory] user_info detected, storing original (q_len={len(question)}, a_len={len(answer)})")
            return {
                "question_summary": question,
                "answer_summary": answer[:100] + "..." if len(answer) > 100 else answer
            }

        # medical 타입은 요약
        print(f"• [Memory] medical type, generating summary via GPT-4o-mini...")
        prompt = f"""다음 의학 대화를 각각 1-2줄로 간결하게 요약하세요.

질문: {question}

답변: {answer}

JSON 형식으로 출력:
{{
  "question_summary": "질문 요약 (1-2줄)",
  "answer_summary": "답변 요약 (핵심만 1-2줄)"
}}

중요:
- 핵심 정보만 포함 (병명, 증상, 치료법 등)
- 불필요한 상세 내용 제거
- 출처 정보 제외"""

        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        import json
        result = json.loads(res.choices[0].message.content.strip())

        q_summary = result.get("question_summary", question[:100])
        a_summary = result.get("answer_summary", answer[:100])

        print(f"• [Memory] Summary generated (q_summary_len={len(q_summary)}, a_summary_len={len(a_summary)})")

        return {
            "question_summary": q_summary,
            "answer_summary": a_summary
        }

    except Exception as e:
        print(f"• [Memory] Summarization failed: {e}")
        import traceback
        traceback.print_exc()
        # 실패 시 앞부분만 저장
        return {
            "question_summary": question[:100] + "..." if len(question) > 100 else question,
            "answer_summary": answer[:100] + "..." if len(answer) > 100 else answer
        }


def _read_memory(state: SelfRAGState, limit: int = 5) -> SelfRAGState:
    """
    내부 함수: 메모리 읽기
    SQLite에서 최근 대화를 읽어와서 List[Dict[str,str]] 형태로 state에 저장
    가장 최근 대화가 0번째 인덱스

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

        # DB에 저장된 총 대화 개수 확인
        cursor.execute('SELECT COUNT(*) FROM conversation_memory')
        total_count = cursor.fetchone()[0]

        # 실제 불러올 개수 결정 (DB에 저장된 개수와 limit 중 작은 값)
        actual_limit = min(limit, total_count)

        if actual_limit > 0:
            cursor.execute('''
                SELECT question_summary, answer_summary, original_question, assistant_answer
                FROM conversation_memory
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (actual_limit,))
            rows = cursor.fetchall()
        else:
            rows = []

        conn.close()

        if rows:
            # List[Dict[str, str]] 형태로 변환
            # rows는 DESC 순서 (최신→오래된)이므로 그대로 사용
            # 가장 최근 대화가 0번째 인덱스 (최신 이름 우선)
            conversation_list = []
            for q_summary, a_summary, q_original, a_original in rows:  # 최신 → 오래된 순서
                # 원본 사용 (summary는 DB에만 저장, history에는 원본 전달)
                # 이유: 후속 질문에 필요한 세부 정보 보존
                user_content = q_original
                assistant_content = a_original

                conversation_list.append({"role": "user", "content": user_content})
                conversation_list.append({"role": "assistant", "content": assistant_content})

            state["conversation_history"] = conversation_list
            print(f"• [Memory] Loaded {len(rows)} conversations (originals, total {len(conversation_list)} messages, newest→oldest)")
        else:
            # 이전 대화가 없는 경우
            state["conversation_history"] = []
            print("• [Memory] No previous conversations found")

    except Exception as e:
        print(f"• [Memory] Read error: {e}")
        # 오류 시 빈 리스트 설정
        state["conversation_history"] = []

    return state


def _write_memory(state: SelfRAGState) -> SelfRAGState:
    """
    내부 함수: 메모리 쓰기
    현재 대화를 SQLite에 저장

    Args:
        state: 현재 상태 (질문과 답변 포함)

    Returns:
        SelfRAGState: 변경되지 않은 상태 (저장만 수행)
    """
    print("• [Memory] Writing to DB...")

    try:
        # 답변 추출
        structured_answer = state.get("structured_answer", {})
        if structured_answer and "answer" in structured_answer:
            assistant_answer = structured_answer["answer"]
        else:
            assistant_answer = state.get("final_answer", "")

        # 답변이 없으면 저장 안 함
        if not assistant_answer:
            print("• [Memory] Skip: no answer")
            return state

        # 에러 메시지는 저장 안 함
        skip_phrases = [
            "관련 정보를 찾을 수 없습니다",
            "관련 문서를 찾을 수 없습니다",
            "죄송합니다. 저는 의학 질문에만 답할 수 있습니다"
        ]

        if any(phrase in assistant_answer for phrase in skip_phrases):
            print("• [Memory] Skip: error message")
            return state

        # 저장할 데이터 준비
        original_question = state.get("original_question") or state.get("question", "")
        conversation_type = state.get("conversation_type", "medical")

        # 요약 생성 (토큰 절약)
        print(f"• [Memory] Generating summary (type={conversation_type})...")
        summaries = _summarize_conversation(original_question, assistant_answer, conversation_type)
        question_summary = summaries["question_summary"]
        answer_summary = summaries["answer_summary"]

        print(f"• [Memory] Saving to DB:")
        print(f"  - original_question: {original_question[:50]}...")
        print(f"  - question_summary: {question_summary[:50] if question_summary else 'NULL'}...")
        print(f"  - answer_summary: {answer_summary[:50] if answer_summary else 'NULL'}...")

        # SQLite에 저장
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        timestamp = datetime.now().isoformat()

        cursor.execute('''
            INSERT INTO conversation_memory
            (timestamp, original_question, assistant_answer, question_summary, answer_summary, conversation_type)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (timestamp, original_question, assistant_answer, question_summary, answer_summary, conversation_type))

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

        print(f"• [Memory] ✅ Successfully saved conversation (type={conversation_type})")

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
    30일 이상 데이터 삭제
    """
    print("• [Memory Transform] Starting cleanup...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 30일 이상 데이터 삭제
    cursor.execute('''
        DELETE FROM conversation_memory
        WHERE datetime(timestamp) < datetime('now', '-30 days')
    ''')

    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()

    print(f"• [Memory Transform] Deleted {deleted_count} old conversations")


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
    print("• [Memory Write] start")
    state = _write_memory(state)

    # 턴 카운터 증가 및 주기적 정리
    turn_count = _increment_turn_count()
    if turn_count % TRANSFORM_INTERVAL == 0:
        _transform_memory()

    print("• [Memory Write] complete")
    return state
