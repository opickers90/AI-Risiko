from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render  # noqa
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, ListView

from ai_risiko.post.models import Post


class PostListView(LoginRequiredMixin, ListView):
    template_name = "post/post_list.html"
    paginate_by = 5
    model = Post

    def get_queryset(self):
        """
        List PUBLISHED Posts in descending id order.
        """
        qs = super().get_queryset()
        qs = qs.filter(status="PUBLISHED")
        qs = qs.order_by("-id")
        return qs

    def dispatch(self, request, *args, **kwargs):
        """ """
        return super().dispatch(request, *args, **kwargs)


class PostDetailView(LoginRequiredMixin, DetailView):
    """
    Detail page about a Post.
    """

    template_name = "post/post_detail.html"
    model = Post

    def dispatch(self, request, *args, **kwargs):
        """ """
        instance = self.get_object()
        if instance.status != "PUBLISHED":
            messages.error(self.request, _("Cannot view this post!"))
            return redirect("newdashboard:post-list")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # instance = self.object
        fullscreen = self.request.GET.get("fullscreen", None)
        if fullscreen == "1":
            self.template_name = "post/post_detail_fullscreen.html"
        return context
