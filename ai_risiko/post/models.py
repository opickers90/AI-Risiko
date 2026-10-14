from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class Post(models.Model):
    """ """

    class PostStatus(models.TextChoices):
        DRAFT = "DRAFT", _("Draft")
        PUBLISHED = "PUBLISHED", _("Published")

    class PostVisibility(models.TextChoices):
        OWN_DASHBOARD = "OWN_DASHBOARD", _("Own Dashboard (visible on own dashboard)")
        PUBLIC_DASHBOARD = "PUBLIC_DASHBOARD", _(
            "Public Dashboard (visible on all user dashboards)"
        )

    class PostFormat(models.TextChoices):
        TEXT = "TEXT", _("Text")
        HTML = "HTML", _("HTML")

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    title = models.CharField(
        max_length=255,
        help_text=_("Provide a title of the post."),
    )
    user = models.ForeignKey(
        User, models.SET_NULL, related_name="posts", null=True, blank=True
    )
    teaser = models.CharField(
        blank=True,
        max_length=255,
        help_text=_("Optional teaser text about the post."),
    )
    content = models.TextField(
        help_text=_(
            "Mandatory post content.<br>Warning: HTML format posts with broken content may break the page!"
        ),
    )
    status = models.CharField(
        max_length=255,
        choices=PostStatus.choices,
        help_text=_("Status of post."),
    )
    visibility = models.CharField(
        max_length=255,
        choices=PostVisibility.choices,
        help_text=_("Visibility of post."),
    )
    format = models.CharField(
        max_length=255,
        choices=PostFormat.choices,
        help_text=_(
            "Format of post.<br>Warning: HTML format posts with broken content may break the page!"
        ),
    )
    order = models.IntegerField(
        null=True, blank=True, help_text=_("Order of post, the lower value the higher.")
    )
    promoted = models.BooleanField(
        null=True,
        blank=True,
        help_text=_(
            "If post is set to published, public dashboard, and promoted then the user will be redirect to"
            " that post on dashboard login."
        ),
    )
    url_parameters = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("URL parameters"),
        help_text=_(
            "Optional URL parameters to append to the post link, example: fullscreen=1."
        ),
    )

    def __str__(self):
        return f"Post => ID: {self.id}" f" - Title: {self.title}"
