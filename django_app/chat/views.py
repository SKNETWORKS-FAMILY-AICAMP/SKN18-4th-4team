import json
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import ChatConversation, Message, MessageFeedback
from .services import generate_ai_response, generate_concept_graph, summarize_conversation_title


QUICK_TEMPLATES_PATH = Path(__file__).resolve().parent / "data" / "quick_templates.json"

def _load_quick_templates():
    """
    빠른 질문 템플릿(quick_templates.json)을 로드하여
    적합하게 정제된 섹션 리스트를 반환합니다.

    - 파일 위치: QUICK_TEMPLATES_PATH
    - 예외 발생 시(파일 없음 또는 JSON 에러): 빈 리스트 반환
    - items 항목이 비어있는 경우 해당 section은 제거
    """
    try:
        with QUICK_TEMPLATES_PATH.open(encoding="utf-8") as fp:
            data = json.load(fp)
    except (FileNotFoundError, json.JSONDecodeError):
        # 파일이 없거나, JSON 파싱 실패 시 빈 리스트 반환
        return []

    sections = data.get("sections", [])
    formatted = []
    # 각 섹션에 대해 items가 비어있지 않은 경우만 필터링 및 정제
    for section in sections:
        items = [item for item in section.get("items", []) if item]
        if items:
            formatted.append(
                {
                    "title": section.get("title", ""),
                    "items": items,
                }
            )
    return formatted

QUICK_TEMPLATE_SECTIONS = _load_quick_templates()


def _safe_reverse(name: str, default: str) -> str:
    """
    주어진 URL name으로 reverse를 시도하고,
    만약 NoReverseMatch 에러가 발생하면 기본값(default) 경로 반환 
    이는 URL 패턴이 없거나 잘못된 경우에도 안전하게 기본 경로를 사용 가능
    """
    try:
        return reverse(name)
    except NoReverseMatch:
        return default


def _serialize_conversation(conversation: ChatConversation) -> dict:
    """
    단일 ChatConversation 인스턴스를 직렬화하여 프론트엔드 전달에 적합한 dict 형태로 반환

    반환 필드:
      - id: 대화의 고유 ID (str)
      - title: 대화 제목 (str)
      - last_message_preview: 마지막 메시지 미리보기 (str)
      - updated_at: 마지막 활동 시각(존재 시), 없으면 생성 시각(isoformat, str)
    """
    return {
        "id": str(conversation.id),
        "title": conversation.title,
        "last_message_preview": conversation.last_message_preview,
        "updated_at": (conversation.last_activity_at or conversation.created_at).isoformat(),
    }


def _serialize_message(message: Message, user=None) -> dict:
    reason_code = ""
    reason_text = ""
    if user and user.is_authenticated:
        entry = message.feedback_entries.filter(user=user).first()
        if entry:
            reason_code = entry.reason_code or ""
            reason_text = entry.reason_text or ""
    return {
        "id": str(message.id),
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at.isoformat(),
        "citations": message.citations or [],
        "feedback": message.feedback or "",
        "metadata": message.metadata or {},
        "reference_type": message.reference_type or (message.metadata or {}).get("reference_type") or "",
        "feedback_reason_code": reason_code,
        "feedback_reason_text": reason_text,
    }

@login_required(login_url="accounts:login")
def index(request):
    """
    채팅 메인 페이지 렌더링 뷰.
    
    - 인증된 사용자인 경우, 해당 사용자가 생성한 is_archived=False 조건의 ChatConversation 목록을 최신순으로 쿼리해서
      기본 정보(아이디, 제목, 마지막 미리보기, 시간)를 initial_conversations로 템플릿에 전달.
    - 인증되지 않은 경우엔 빈 대화 리스트 전달.
    - 사용자 이름, 이메일 등은 user model 정보에서 가져오되, 없으면 기본값 사용.
    - main_url, logout_url은 reverse 실패 시 기본값 사용(_safe_reverse).
    - quick_template_sections는 FAQ/퀵질문 템플릿 데이터 여럿.
    - context를 chat/chat.html 템플릿에 전달.
    """
    user = request.user
    conversations = []
    if user.is_authenticated:
        # 인증된 사용자: 본인이 만든, 보관처리 안된 대화만 쿼리, 최신순 정렬
        conversations_qs = (
            ChatConversation.objects.filter(created_by=user, is_archived=False)
            .order_by("-last_activity_at", "-created_at")
            .only("id", "title", "last_message_preview", "last_activity_at", "created_at")
        )
        # 쿼리셋을 직렬화해서 리스트로 변환
        conversations = [_serialize_conversation(conv) for conv in conversations_qs]

    context = {
        "user_name": (user.get_full_name() or user.get_username() or "게스트 연구자")
        if user.is_authenticated
        else "게스트 연구자",
        "user_email": user.email if getattr(user, "email", None) else "research@example.com",
        "main_url": _safe_reverse("main:main", "/main/"),  # 메인 화면으로 가는 URL
        "logout_url": _safe_reverse("accounts:logout", "/accounts/logout/"),  # 로그아웃 URL
        "quick_template_sections": QUICK_TEMPLATE_SECTIONS,  # FAQ 빠른질문 템플릿
        "initial_conversations": conversations,  # 대화 내역 초기 전달용(프론트 localStorage와 동기화)
    }
    return render(request, "chat/chat.html", context)

def conversation_list(request):
    """
    인증된 사용자의 대화(conversation) 리스트를 반환하는 API 뷰

    - 인증이 안 된 경우 401 반환
    - 인증된 경우, 본인이 만든 보관 안 된 대화만 최신순으로 반환
    - 각 대화는 _serialize_conversation 함수로 직렬화됨

    반환 예시:
      {
        "conversations": [
          {
            "id": "1",
            "title": "임상시험 검색",
            "last_message_preview": "최근 논문 3건을 찾았습니다.",
            "updated_at": "2024-06-14T09:00:00Z"
          },
          ...
        ]
      }
    """
    if not request.user.is_authenticated:
        # 인증 안 된 경우 에러 반환
        return JsonResponse({"error": "unauthorized"}, status=401)

    if request.method == "POST":
        payload = json.loads(request.body or "{}")
        title = payload.get("title") or ChatConversation.DEFAULT_TITLE
        conversation = ChatConversation.objects.create(
            title=title,
            created_by=request.user,
            last_activity_at=timezone.now(),
        )
        return JsonResponse({"conversation": _serialize_conversation(conversation)}, status=201)

    # 본인 생성 & 보관하지 않은 대화만 쿼리, 최신순 정렬
    conversations_qs = (
        ChatConversation.objects.filter(created_by=request.user, is_archived=False)
        .order_by("-last_activity_at", "-created_at")
        .only("id", "title", "last_message_preview", "last_activity_at", "created_at")
    )
    # 쿼리셋을 직렬화 리스트로 변환
    conversations = [_serialize_conversation(conv) for conv in conversations_qs]
    # JSON 응답 반환
    return JsonResponse({"conversations": conversations})


def conversation_detail(request, conversation_id):
    """
    지정된 대화(conversation)의 상세 정보 및 메시지 목록을 반환하거나
    대화를 아카이브(삭제) 처리하는 API 뷰

    - 인증되지 않은 사용자는 401 반환
    - DELETE 메소드: 해당 대화를 아카이브(soft delete, is_archived=True) 하고 "deleted" 반환
    - GET 등 기타 메소드: 대화 정보와 메시지 목록(최신순) JSON 반환

    Args:
        request: Django HttpRequest 객체
        conversation_id: 조회할 대화의 id(pk)

    Returns:
        - 인증 실패시: {"error": "unauthorized"}, 401
        - DELETE 성공시: {"status": "deleted"}, 200
        - GET 성공시: {
            "conversation": {...},
            "messages": [...]
          }, 200
        - 404: 해당 대화가 없거나 접근 권한이 없음
    """
    # 1. 인증되지 않은 사용자 차단
    if not request.user.is_authenticated:
        return JsonResponse({"error": "unauthorized"}, status=401)

    # 2. 요청 사용자가 만든, 아카이브되지 않은 해당 대화 조회 (없으면 404)
    conversation = get_object_or_404(
        ChatConversation,
        id=conversation_id,
        created_by=request.user,
        is_archived=False,
    )

    # 3. DELETE 요청이면 대화를 soft delete 처리(아카이브) 후 결과 반환
    if request.method == "DELETE":
        conversation.is_archived = True
        conversation.save(update_fields=["is_archived"])
        return JsonResponse({"status": "deleted"})

    # 4. 그 외(GET 등) 요청이면 대화 정보와 메시지 목록 반환
    # 대화 내 모든 메시지를 직렬화하여 반환
    messages = [_serialize_message(msg, request.user) for msg in conversation.messages.all()]
    return JsonResponse(
        {
            "conversation": _serialize_conversation(conversation),
            "messages": messages,
        }
    )

def conversation_messages(request, conversation_id):
    """
    지정된 대화(conversation)에 새 메시지를 추가

    요구사항:
    - 인증된 사용자만 호출 가능
    - POST 메서드만 허용
    - body: { "content": (메시지 내용) } 필수

    주요 처리:
    1. 인증 확인: 인증되지 않은 경우 401 반환
    2. 대화 조회: 존재하지 않거나 본인이 아니거나 아카이브된 경우 404 반환
    3. POST 이외의 메소드 차단 (405 반환)
    4. content 필드 미입력 시 400 반환
    5. Message 생성(유저 역할, content 저장) 및 마지막 활동 갱신(preview 갱신)
    6. 생성 메시지 json 응답(201 반환)
    """
    # 1. 인증되지 않은 유저는 401 반환
    if not request.user.is_authenticated:
        return JsonResponse({"error": "unauthorized"}, status=401)

    # 2. 본인이 만든, 아카이브되지 않은 해당 conversation 발견
    conversation = get_object_or_404(
        ChatConversation,
        id=conversation_id,
        created_by=request.user,
        is_archived=False,
    )

    # 3. 허용된 메서드 확인 (POST만 가능)
    if request.method != "POST":
        return JsonResponse({"error": "method_not_allowed"}, status=405)

    # 4. 본문에서 content 추출 및 체크
    payload = json.loads(request.body or "{}")
    content = (payload.get("content") or "").strip()
    if not content:
        return JsonResponse({"error": "content_required"}, status=400)

    # 5. 사용자 메시지 생성
    user_message = Message.objects.create(
        conversation=conversation,
        role="user",
        content=content,
    )
    conversation.update_activity(preview=content)

    # 6. AI 응답 생성 및 저장
    try:
        ai_text, citations, scores, reference_type = generate_ai_response(conversation, content)
    except Exception as exc:  # LLM 호출 실패
        return JsonResponse(
            {
                "messages": [
                    _serialize_message(user_message, request.user),
                ],
                "error": str(exc),
            },
            status=201,
        )

    metadata = {"reference_type": reference_type} if reference_type else {}
    assistant_message = Message.objects.create(
        conversation=conversation,
        role="assistant",
        content=ai_text,
        citations=citations,
        llm_score=scores.get("llm_score") if isinstance(scores, dict) else None,
        relevance_score=scores.get("relevance_score") if isinstance(scores, dict) else None,
        metadata=metadata or None,
        reference_type=reference_type or "",
    )
    conversation.update_activity(preview=ai_text)

    if not conversation.title or conversation.title == ChatConversation.DEFAULT_TITLE:
        try:
            summary = summarize_conversation_title(content)
            conversation.title = summary
            conversation.save(update_fields=["title"])
        except Exception as exc:
            # 요약 실패 시 로그만 남기고 계속 진행
            print(f"[title summarize error] {exc}")

    return JsonResponse(
        {
            "messages": [
                _serialize_message(user_message, request.user),
                _serialize_message(assistant_message, request.user),
            ]
        },
        status=201,
    )


def message_feedback(request, message_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "unauthorized"}, status=401)

    if request.method != "PATCH":
        return JsonResponse({"error": "method_not_allowed"}, status=405)

    message = get_object_or_404(
        Message,
        id=message_id,
        conversation__created_by=request.user,
    )

    payload = json.loads(request.body or "{}")
    feedback = (payload.get("feedback") or "").strip()
    if feedback not in ("positive", "negative", ""):
        return JsonResponse({"error": "invalid_feedback"}, status=400)

    message.feedback = feedback
    message.save(update_fields=["feedback"])

    if feedback == "positive":
        MessageFeedback.objects.update_or_create(
            message=message,
            user=request.user,
            defaults={"reason_code": "positive", "reason_text": ""},
        )
    elif feedback == "negative":
        reason_code = payload.get("reason_code") or ""
        valid_codes = {choice[0] for choice in MessageFeedback.REASON_CHOICES if choice[0] != "positive"}
        if reason_code not in valid_codes:
            return JsonResponse({"error": "invalid_reason"}, status=400)
        reason_text = (payload.get("reason_text") or "").strip()
        if reason_code == "other" and not reason_text:
            return JsonResponse({"error": "reason_text_required"}, status=400)
        MessageFeedback.objects.update_or_create(
            message=message,
            user=request.user,
            defaults={"reason_code": reason_code, "reason_text": reason_text},
        )
    else:
        MessageFeedback.objects.filter(message=message, user=request.user).delete()

    return JsonResponse({"message": _serialize_message(message, request.user)})


@require_POST
def message_concept_graph(request, message_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "unauthorized"}, status=401)

    message = get_object_or_404(
        Message,
        id=message_id,
        conversation__created_by=request.user,
        role="assistant",
    )

    if not message.concept_graph:
        try:
            graph_code = generate_concept_graph(message)
            message.concept_graph = graph_code
            message.save(update_fields=["concept_graph"])
        except Exception as exc:
            return JsonResponse({"error": str(exc)}, status=500)

    return JsonResponse({"graph": message.concept_graph})
