from django.urls import path
from . import views

app_name = "chat"
urlpatterns = [
    path("", views.index, name="chat"),
    path("api/conversations/", views.conversation_list, name="conversation_list"),
    path(
        "api/conversations/<int:conversation_id>/",
        views.conversation_detail,
        name="conversation_detail",
    ),
    path(
        "api/conversations/<int:conversation_id>/messages/",
        views.conversation_messages,
        name="conversation_messages",
    ),
    path(
        "api/messages/<int:message_id>/feedback/",
        views.message_feedback,
        name="message_feedback",
    ),
    path(
        "api/messages/<int:message_id>/concept-graph/",
        views.message_concept_graph,
        name="message_concept_graph",
    ),
]
