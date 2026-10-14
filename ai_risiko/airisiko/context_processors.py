from django.conf import settings


def ai_risiko_last_updated(request):
    return {
        "AI_RISIKO_LAST_UPDATED": settings.AI_RISIKO_LAST_UPDATED,
    }
