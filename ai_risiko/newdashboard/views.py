import urllib.parse

from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from ai_risiko.airisiko.models import OpenquakeJob
from ai_risiko.airisiko.templatetags.airisiko_tags import airisiko_get_post


def index(request):
    """ """
    if not request.user.is_authenticated:
        return redirect("newdashboard:login")
    openquake_completed_jobs = OpenquakeJob.objects.filter(
        user=request.user, job_status="complete"
    ).count()
    context = {"openquake_completed_jobs": openquake_completed_jobs}
    return render(request, "newdashboard/index.html", context)


def login(request):
    """ """
    if request.user.is_authenticated:
        return redirect("newdashboard:index")
    return render(request, "newdashboard/login.html", {})


@login_required
def redirect_to_promoted_post(request):
    """
    Check for first "PUBLIC_DASHBOARD" post in ascending order that is published and promoted.
    If found then redirect to the post detail page.
    """
    post = airisiko_get_post(
        "admin,admin_airisiko", "PUBLISHED", "PUBLIC_DASHBOARD", promoted=True
    )
    if post:
        url_parameters = ""
        if post.url_parameters:
            url_parameters = "?{}".format(
                urllib.parse.quote_plus(post.url_parameters, safe="=&")
            )
        return redirect(
            reverse("newdashboard:post-detail", kwargs={"pk": post.id}) + url_parameters
        )
    return redirect("newdashboard:index")


@login_required
def logout(request):
    """ """
    messages.info(request, _("You have been successfully logged out!"))
    auth_logout(request)
    return redirect("newdashboard:login")


@login_required
def my_profile(request):
    """ """
    context = {}
    return render(request, "newdashboard/my_profile.html", context)


@login_required
def preferences(request):
    """ """
    context = {}
    return render(request, "newdashboard/preferences.html", context)
