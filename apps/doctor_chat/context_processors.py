from django.db.models import Q
from .models import ChatMessage


def unread_chat_count(request):
    """Adds {{ unread_chat_count }} to every template's context automatically."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}

    count = ChatMessage.objects.filter(
        Q(assignment__mother=user) | Q(assignment__doctor=user),
        is_read=False, assignment__is_active=True,
    ).exclude(sender=user).count()

    return {"unread_chat_count": count}