from allauth.account.views import ConfirmEmailView
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import include, path
from django.views import defaults as default_views
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from filebrowser.sites import site

from ai_risiko.dashboard.views import (
    VulnerabilityInformationDetailView,
    VulnerabilityInformationListView,
)

# from rest_framework.authtoken.views import obtain_auth_token


urlpatterns = [
    # path("", TemplateView.as_view(template_name="pages/home.html"), name="home"),
    # path(
    #     "about/", TemplateView.as_view(template_name="pages/about.html"), name="about"
    # ),
    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL + "filebrowser/", site.urls),
    path(settings.ADMIN_URL, admin.site.urls),
    # User management
    path("users/", include("ai_risiko.users.urls", namespace="users")),
    path("accounts/", include("allauth.urls")),
    # Your stuff: custom urls includes go here
    path(
        "", TemplateView.as_view(template_name="ai_risiko/pages/home.html"), name="home"
    ),
    path("dashboard/", include("ai_risiko.dashboard.urls", namespace="dashboard")),
    path(
        "newdashboard/",
        include("ai_risiko.newdashboard.urls", namespace="newdashboard"),
    ),
    path(
        "about/",
        TemplateView.as_view(template_name="ai_risiko/pages/about.html"),
        name="about",
    ),
    path(
        "vulnerability/",
        VulnerabilityInformationListView.as_view(),
        name="vulnerabilityinformation-list",
    ),
    path(
        "vulnerability/<int:pk>/",
        VulnerabilityInformationDetailView.as_view(),
        name="vulnerabilityinformation-detail",
    ),
    path(
        "mazer/base/",
        staff_member_required(TemplateView.as_view(template_name="mazer/base.html")),
        name="mazer-base",
    ),
    path(
        "mazer/layout-default/",
        staff_member_required(
            TemplateView.as_view(template_name="mazer/layout_default.html")
        ),
        name="mazer-layout-default",
    ),
    path(
        "mazer/layout-horizontal/",
        staff_member_required(
            TemplateView.as_view(template_name="mazer/layout_horizontal.html")
        ),
        name="mazer-layout-horizontal",
    ),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# API URLS
urlpatterns += [
    # API base url
    path("api/", include("config.api_router", namespace="api")),
    # DRF auth token
    # path("auth-token/", obtain_auth_token),
    # use Dj-Rest-Auth instead of default DRF auth token
    path("rest-auth/", include("dj_rest_auth.urls")),
    # temporary workaround override for account email confirmation
    # refer to https://github.com/iMerica/dj-rest-auth/issues/17
    path(
        "rest-auth/register/account-confirm-email/<str:key>/",
        ConfirmEmailView.as_view(),
        name="account_confirm_email",
    ),
    path("rest-auth/register/", include("dj_rest_auth.registration.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-docs",
    ),
    # DRF login/logout menu
    # api login/logout now only works via dj-rest-auth at /rest-auth/login/ /rest-auth/logout/
    # path("api/auth/", include("rest_framework.urls")),
]

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
