import os
import sys
from dotenv import load_dotenv
from pathlib import Path

# =========================
# 1. 환경 설정
# =========================
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# =========================
# 2. 전처리 및 청킹 단계
# =========================
from rag.etl.transform.cleaner import main as clean_main
from rag.etl.transform.chunker import main as chunk_main

print("🚀 [1단계] 데이터 전처리 시작...")
clean_main()
print("✅ 데이터 전처리 완료!\n")

print("🚀 [2단계] 청킹(chunking) 시작...")
chunk_main()
print("✅ 청킹 완료!\n")

# =========================
# 3. 임베딩 및 벡터 저장 단계
# =========================
from rag.etl.load.csvloader import CustomCSVLoader
from rag.services.db_pool import DatabasePool
from rag.services.vectorstore_pg import CustomPGVector
from langchain_openai import OpenAIEmbeddings


def add_documents_in_batches(store, docs, batch_size=100):
    total = len(docs)
    for i in range(0, total, batch_size):
        batch = docs[i:i + batch_size]
        print(f"🔹 임베딩 중... {i + len(batch)}/{total}")
        store.add_documents(batch)
    print("✅ 전체 임베딩 및 저장 완료.")


def main():
    print("🚀 [3단계] CSV 로드 및 임베딩 시작...")

    loader = CustomCSVLoader(
        file_path="rag/data/T3_chunked2.csv",
        content_columns=["chunk_text"],
        metadata_columns=["c_id"]
    )
    docs = loader.load()
    if not docs:
        print("⚠️ CSV에서 로드된 문서가 없습니다.")
        return

    db = DatabasePool()
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    store = CustomPGVector(db=db, embedding_fn=embeddings, table="medical")

    add_documents_in_batches(store, docs, batch_size=100)

    print("🎯 전체 파이프라인 완료!")


if __name__ == "__main__":
    main()
