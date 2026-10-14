import datetime
import os

from django import template
from django.conf import settings
from django.urls import reverse

from ai_risiko.airisiko.models import (
    CalculationServer,
    ExposureRecapitulation,
    OpenquakeAAL,
    OpenquakePML,
)
from ai_risiko.post.models import Post

register = template.Library()


@register.simple_tag
def airisiko_active_url(request, url_name, by_url_path=False):
    """
    Return the string 'active' if current request.path is same as name.

    Args:
    - request: Django request object
    - url_name: name of the url or the actual path
    - by_url_path: True if url name contains a url path instead of url name
    """
    if by_url_path:
        path = url_name
    else:
        path = reverse(url_name)
    if request.path == path:
        return "active"
    # if path != "/" and path in request.path:
    #     return "active"
    return ""


@register.simple_tag
def airisiko_settings_value(name):
    """
    Get a value from the settings file.

    Usage:
    {% airisiko_settings_value "SETTINGS_NAME" %}
    """
    return getattr(settings, name, "")


@register.filter
def airisiko_filename(value):
    """
    Return the base file name.

    Usage:
    {{ instance.filefield|airisiko_filename }}
    """
    try:
        return os.path.basename(value.file.name)
    except Exception:
        return ""


@register.simple_tag
def airisiko_check_active_calculation_server(type):
    """
    Check if any calculation servers are currently active.

    Args:
    type (str)

    Returns:
    bool
    """
    return CalculationServer.objects.filter(
        type=type, enabled=True, active=True
    ).exists()


@register.filter
def airisiko_seconds_to_minutes(value):
    """
    Convert seconds to minutes.

    Usage:
    {{ field|airisiko_seconds_to_minutes }}
    """
    try:
        return int(int(value) / 60)
    except Exception:
        return ""


@register.simple_tag
def airisiko_openquakejob_has_risk_matrix(openquakejob):
    """
    Check if OpenQuake job has supporting AAL, PML, and Exposure Recapitulation data
    in order to output Risk Matrix page.

    Usage:
    {% airisiko_has_risk_matrix openquakejob as has_risk_matrix %}
    """
    has_risk_matrix = False
    has_aal = OpenquakeAAL.objects.filter(openquakejob=openquakejob).exists()
    has_pml = OpenquakePML.objects.filter(openquakejob=openquakejob).exists()
    has_exposure_recap = ExposureRecapitulation.objects.filter(
        exposure=openquakejob.exposure
    ).exists()
    if has_aal and has_pml and has_exposure_recap:
        has_risk_matrix = True
    return has_risk_matrix


@register.simple_tag
def airisiko_exposure_has_recapitulation(exposureupload):
    """
    Check if ExposureUpload has supporting Exposure Recapitulation data
    in order to output Exposure Recapitulation page.

    Usage:
    {% airisiko_exposure_has_recapitulation exposureupload as has_exposure_recapitulation %}
    """
    has_recapitulation = False
    exposure = exposureupload.exposures.all().first()
    if exposure:
        has_recapitulation = ExposureRecapitulation.objects.filter(
            exposure=exposure
        ).exists()
    return has_recapitulation


@register.filter
def airisiko_reverse_divide(value, dividee):
    """
    Reverse divide a dividee by value.

    Usage:
    {{ field|airisiko_reverse_divide:1 }}
    """
    try:
        return float(dividee) / float(value)
    except Exception:
        return ""


@register.simple_tag
def airisiko_copyright_years(start_year):
    """Output copyright year range (start_year - current_year).

    Usage:
        {% airisiko_copyright_years 2023 %}
    """
    current_year = datetime.datetime.now().year
    if start_year < current_year:
        return f"{str(start_year)} - {str(current_year)}"
    else:
        return start_year


@register.simple_tag
def airisiko_get_post(
    username,
    status,
    visibility,
    post_id=None,
    return_one=True,
    order_asc=True,
    promoted=False,
):
    """
    Get posts.

    Args:
    username (str): may be separated by comma
    status (str)
    visibility (str)
    post_id (int)
    order_asc (bool)
    promoted (bool)
    return_one (bool)

    Usage:
        {% airisiko_get_post "admin,admin_airisiko" "PUBLISHED" "PUBLIC_DASHBOARD" as latest_admin_public_post %}

    Returns:
    queryset
    """
    usernames = [x.strip() for x in username.split(",")]
    posts = Post.objects.filter(
        user__username__in=usernames, status=status, visibility=visibility
    ).select_related("user")
    if post_id:
        posts = posts.filter(id=post_id)
    if order_asc:
        posts = posts.order_by("order")
    if promoted:
        posts = posts.filter(promoted=promoted)
    if return_one:
        posts = posts.first()
    return posts
