"""
medical 테이블을 사용하는 vectorstore 설정
"""
from rag.services.custom_vectorstore import create_vectorstore as create_custom_vectorstore

def create_vectorstore():
    """
    커스텀 vectorstore 생성 (medical 테이블 사용)
    """
    return create_custom_vectorstore()


if __name__ == "__main__":
    # 테스트
    try:
        vectorstore = create_vectorstore()
        print("✅ pgvector 연결 성공!")

        # 간단한 테스트 검색
        results = vectorstore.similarity_search("당뇨병", k=1)
        print(f"검색 결과 수: {len(results)}")

    except Exception as e:
        print(f"❌ 연결 실패: {e}")