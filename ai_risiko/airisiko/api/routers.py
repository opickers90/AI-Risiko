from django.utils.safestring import mark_safe
from rest_framework.routers import APIRootView, DefaultRouter


class AiRisikoAPIRootView(APIRootView):
    """
    Modify appearance of the API root view.
    """

    def get_view_name(self):
        return "AI Risiko API"

    def get_view_description(self, html=False):
        text = "Browsable API for AI Risiko"
        if html:
            return mark_safe(f"<p>{text}</p>")
        else:
            return text


class AiRisikoAPIDefaultRouter(DefaultRouter):
    APIRootView = AiRisikoAPIRootView
