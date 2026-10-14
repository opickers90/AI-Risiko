from django.contrib import admin

from .models import Post


class PostAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "created",
        "updated",
        "user",
        "status",
        "visibility",
        "order",
        "url_parameters",
        "promoted",
    )
    list_select_related = [
        "user",
    ]
    list_display_links = ("title",)
    list_filter = ["status", "visibility", "promoted"]
    search_fields = ["title", "user__username"]


admin.site.register(Post, PostAdmin)
