from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AiriskoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ai_risiko.airisiko"
    verbose_name = _("AI Risiko")
