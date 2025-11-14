# ============================================
#   완전체 single memory_node (전체 기능 통합)
# ============================================

import sqlite3
from pathlib import Path
from typing import List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
from graph.state import SelfRAGState

# ----------------------------
#  전역 설정
# ----------------------------
load_dotenv()
client = OpenAI()

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "rag" / "queries" / "chat_memory.sqlite3"


# ----------------------------
#  DB 준비 (한 번만 호출)
# ----------------------------
def ensure_db_ready():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        );

        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            question_summary TEXT,
            answer TEXT,
            answer_summary TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS conversation_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            summary TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        );
        """
    )
    conn.commit()
    conn.close()


# ---------------------------------------------
#   LLM Helper — 요약
# ---------------------------------------------
def summarize(text: str, max_sentences: int = 2) -> str:
    if not text:
        return ""
    prompt = f"""
다음 내용을 {max_sentences}문장 이내로 요약하세요:

{text}
"""
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return res.choices[0].message.content.strip()


# ---------------------------------------------
#   LLM Helper — 재작성
# ---------------------------------------------
def rewrite_question(new_q: str, history: List[str], summaries: List[str]) -> str:
    hist = ""
    for i, (h, s) in enumerate(zip(history, summaries), start=1):
        hist += f"[이전 {i}]\n- 질문: {h}\n- 요약: {s}\n\n"

    prompt = f"""
너는 의료 질문을 맥락에 맞게 재작성하는 AI이다.

이전 질문들:
{hist or "(없음)"}

새로운 질문:
{new_q}

요구사항:
- 이전 질문 흐름과 자연스럽게 이어지게 재작성
- 중복 제거
- 명확하고 간결한 한국어로 표현
- 재작성된 질문만 출력
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return res.choices[0].message.content.strip()


# ---------------------------------------------
#   📌 하나로 합쳐진 단일 Memory Node
# ---------------------------------------------
def memory_node(state: SelfRAGState) -> SelfRAGState:
    """
    ✔ final_answer 없음  → 재작성 모드(rewrite_with_history)
    ✔ final_answer 있음  → 저장 모드(store_summary)

    내부에서:
    - DB 연결
    - 메시지 저장
    - 히스토리 조회
    - 재작성 / 요약
    - memory DB 저장
    - conversation_summaries 저장

    전부 하나의 함수에서 수행.
    """

    ensure_db_ready()

    question = state.get("question", "")
    final_answer = state.get("final_answer", "")
    conversation_id = 1  # 원하는 ID로 세팅 가능

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1) 메시지 저장 (공통)
    cur.execute(
        "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
        (conversation_id, "user", question),
    )
    conn.commit()

    # ========================================
    #   ( A ) 재작성 모드
    # ========================================
    if not final_answer:
        print("• [MemoryNode] mode = rewrite_with_history")

        # 1) memory 테이블에서 모든 과거 기록 불러오기
        cur.execute("SELECT question, question_summary FROM memory ORDER BY id")
        rows = cur.fetchall()

        history = [row["question"] for row in rows]
        summaries = [row["question_summary"] for row in rows]

        # 2) 재작성
        rewritten = rewrite_question(question, history, summaries)
        state["question"] = rewritten

        print(f"• [MemoryNode] rewritten → {rewritten[:60]}...")

        conn.close()
        return state

    # ========================================
    #   ( B ) 저장 모드
    # ========================================
    print("• [MemoryNode] mode = store_summary")

    # 1) assistant 메시지 저장
    cur.execute(
        "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
        (conversation_id, "assistant", final_answer),
    )
    conn.commit()

    # 2) 질문/답변 요약
    q_sum = summarize(question, 1)
    a_sum = summarize(final_answer, 2)

    # 3) 메모리 저장
    cur.execute(
        """
        INSERT INTO memory (question, question_summary, answer, answer_summary)
        VALUES (?, ?, ?, ?)
        """,
        (question, q_sum, final_answer, a_sum),
    )

    # 4) conversation_summaries 업데이트
    cur.execute(
        """
        SELECT role, content
        FROM messages
        WHERE conversation_id = ?
        ORDER BY id DESC
        LIMIT 20
        """,
        (conversation_id,),
    )
    msgs = cur.fetchall()

    convo = "\n".join(
        [("사용자" if m["role"] == "user" else "어시스턴트") + ": " + m["content"] for m in msgs]
    )

    conv_sum = summarize(convo, 1)

    cur.execute(
        "INSERT INTO conversation_summaries (conversation_id, summary) VALUES (?, ?)",
        (conversation_id, conv_sum),
    )

    cur.execute(
        "UPDATE conversations SET title=? WHERE id=?",
        (conv_sum, conversation_id),
    )

    conn.commit()
    conn.close()

    print("• [MemoryNode] stored question/answer summary → DB")

    return state
