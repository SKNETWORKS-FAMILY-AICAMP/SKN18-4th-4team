from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[1] / ".env")      # 루트 .env

def main():
    """
    최초 실행 시 데이터베이스에 샘플 문서/청크/임베딩 데이터를 시드(삽입)하는 함수입니다.
    - 테스트 및 개발 환경에서 데이터 파이프라인 확인 용도
    - 사전 정의된 샘플 데이터를 PostgreSQL(pgvector) DB에 저장
    - 실제 삽입/변환 로직은 추후 구현
    """

    pass

if __name__ == "__main__":
    main()