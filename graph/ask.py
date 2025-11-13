"""
터미널에서 사용자에게 질문을 받으면 질문을 처리하고 답변을 출력하는 프로그램
"""
import os
import sys
from dotenv import load_dotenv

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from rag.services.retriever import get_vector_retriever
from graph.compile import create_medical_rag_workflow

# 환경 변수 로드
load_dotenv()


def initialize_system():
    """
    워크플로우를 초기화해야 하는 이유는, 시스템이 사용자의 질문을 효과적으로 처리하기 위해
    필요한 모든 구성 요소(예: 벡터 리트리버, RAG 워크플로우 등)를 미리 준비해두어야 하기 때문입니다.
    벡터 리트리버가 정상적으로 구성되어야 관련 문서 검색 등 핵심 기능들이 동작하며,
    워크플로우 그래프가 준비되어야 질문 입력 이후의 처리 흐름(분류, 검색, 답변 생성 등)이 자동화됩니다.
    따라서 시스템 시작 시 모든 주요 리소스를 미리 초기화하여
    사용자 질문에 즉시 응답할 수 있는 상태로 만들어 두는 것이 필요합니다.
    """
    print("=" * 60)
    print(" 의료 RAG 시스템 초기화")
    print("=" * 60)

    # VectorRetriever 초기화 및 테스트
    # 벡터 리트리버를 사용하는 이유:
    # 벡터 리트리버는 각 문서(혹은 데이터)의 의미를 임베딩(벡터)로 변환하여 저장하고,
    # 사용자의 질문도 동일하게 벡터로 변환한 뒤, 이 벡터 간의 유사도를 계산하여
    # 의미적으로 가장 가까운(관련성 높은) 문서를 빠르게 찾을 수 있게 해줍니다.
    # 즉, 전통적인 키워드 검색과 달리 의미 기반 검색이 가능하며,
    # 의료 지식 검색 등 답변의 정합성과 정확성이 중요한 분야에서 매우 효과적인 방식입니다.
    # 아래에서 벡터 리트리버를 실제로 초기화합니다.
    try:
        retriever = get_vector_retriever()
        print("✅ VectorRetriever 연결 성공!")

        # 연결 테스트
        test_results = retriever.search("테스트", top_k=1)
        print(f"✅ 검색 테스트 성공 (결과 수: {len(test_results)}개)")
    except Exception as e:
        print(f"❌ VectorRetriever 연결 실패: {e}")
        print("⚠️  retriever 초기화 실패로 인해 시스템을 종료합니다.")
        sys.exit(1)

    # 워크플로우 생성
    medical_app = create_medical_rag_workflow()
    print("✅ Medical RAG 워크플로우 생성 완료!\n")

    return medical_app


def main():
    """메인 함수: 사용자 질문을 받아 처리"""

    # 시스템 초기화
    medical_app = initialize_system()

    print("=" * 60)
    print(" 질문을 입력하세요 (종료: 'quit', 'exit', 'q')")
    print("=" * 60 + "\n")

    # 대화 루프
    while True:
        try:
            # 사용자 입력
            question = input("💬 질문: ").strip()

            # 종료 명령
            if question.lower() in ['quit', 'exit', 'q']:
                print("\n프로그램을 종료합니다. 감사합니다!")
                break

            # 빈 입력 처리
            if not question:
                print("⚠️  질문을 입력해주세요.\n")
                continue

            print()

            # 워크플로우 실행
            result = medical_app.invoke({"question": question})

            # 결과 출력
            print("\n" + "=" * 60)
            print(" 답변")
            print("=" * 60)
            print(result.get('final_answer', '답변을 생성하지 못했습니다.'))
            print("=" * 60 + "\n")

        except KeyboardInterrupt:
            print("\n\n프로그램을 종료합니다. 감사합니다!")
            break

        except Exception as e:
            print(f"\n❌ 오류 발생: {e}\n")


if __name__ == "__main__":
    main()
