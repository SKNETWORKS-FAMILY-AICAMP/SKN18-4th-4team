"""
메모리 기능이 통합된 의료 RAG 시스템
터미널에서 사용자에게 질문을 받으면 질문을 처리하고 답변을 출력
이전 대화를 기억하여 맥락 인식 대화 가능
"""
import os
import sys
from dotenv import load_dotenv

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from rag.services.retriever import get_vector_retriever
from graph.compile_i import create_medical_rag_workflow

# 환경 변수 로드
load_dotenv()


def initialize_system():
    """
    메모리 기능이 통합된 워크플로우 초기화

    기존 시스템 + 메모리 기능:
    - VectorRetriever: 의미 기반 문서 검색
    - Medical RAG Workflow: 질문 처리 파이프라인
    - Memory System: 대화 저장 및 불러오기
      * READ: 이전 대화 자동 로드
      * WRITE: 현재 대화 자동 저장
      * TRANSFORM: 20턴마다 자동 정리 (30일+ & 미사용 대화 삭제)
    """
    print("=" * 60)
    print(" 의료 RAG 시스템 초기화 (메모리 기능 포함)")
    print("=" * 60)

    # VectorRetriever 초기화 및 테스트
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

    # 메모리 통합 워크플로우 생성
    medical_app = create_medical_rag_workflow()
    print("✅ Medical RAG 워크플로우 생성 완료 (메모리 통합)!")
    print("   - 이전 대화 자동 불러오기")
    print("   - 대화 자동 저장 (facts 추출)")
    print("   - 20턴마다 자동 정리\n")

    return medical_app


def print_memory_info(result):
    """
    메모리 정보 출력 (디버깅/정보 제공용)

    Args:
        result: 워크플로우 실행 결과
    """
    # 새로운 List[Dict[str, str]] 형식
    conv_history = result.get("conversation_history", [])

    if conv_history:
        # 대화 턴 수 계산 (user + assistant = 1턴)
        turn_count = len(conv_history) // 2
        print("\n💾 메모리 정보:")
        print(f"   - 불러온 대화: {turn_count}턴 ({len(conv_history)}개 메시지)")

        # 가장 최근 대화 미리보기
        if len(conv_history) >= 2:
            print(f"   - 최근 질문: {conv_history[0].get('content', '')[:50]}...")
            print(f"   - 최근 답변: {conv_history[1].get('content', '')[:50]}...")


def main():
    """메인 함수: 메모리 기능을 갖춘 대화형 시스템"""

    # 시스템 초기화
    medical_app = initialize_system()

    print("=" * 60)
    print(" 질문을 입력하세요 (종료: 'quit', 'exit', 'q')")
    print(" 이전 대화를 기억하여 연속 대화가 가능합니다!")
    print("=" * 60 + "\n")

    # 대화 카운터
    turn_count = 0

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
            turn_count += 1

            # 워크플로우 실행 (메모리 자동 처리)
            # recursion_limit 설정으로 무한 루프 방지
            result = medical_app.invoke(
                {"question": question},
                config={"recursion_limit": 50}
            )

            # 메모리 정보 출력 (선택적)
            # print_memory_info(result)

            # 결과 출력 - JSON 형태와 평문 형태 모두 지원
            if 'structured_answer' in result and result['structured_answer']:
                # JSON 구조화된 답변 출력
                print("\n" + "=" * 60)
                print(" 답변")
                print("=" * 60)
                import json
                print(json.dumps(result['structured_answer'], ensure_ascii=False, indent=2))
                print("=" * 60)
            elif 'final_answer' in result:
                # 평문 답변 출력
                print("\n" + "=" * 60)
                print(" 답변")
                print("=" * 60)
                print(result.get('final_answer', '답변을 생성하지 못했습니다.'))
                print("=" * 60)
            else:
                print("\n⚠️  답변을 생성하지 못했습니다.\n")

            # 턴 정보 출력
            print(f"\n[턴 {turn_count}] ", end="")
            if turn_count % 20 == 0:
                print("🧹 메모리 정리 완료!")
            else:
                print(f"다음 정리까지: {20 - (turn_count % 20)}턴")
            print()

        except KeyboardInterrupt:
            print("\n\n프로그램을 종료합니다. 감사합니다!")
            break

        except Exception as e:
            print(f"\n❌ 오류 발생: {e}\n")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
