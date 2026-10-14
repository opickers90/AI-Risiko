from django.contrib.auth.decorators import login_required
from django.urls import path
from django.views.generic import TemplateView

from ai_risiko.dashboard.views import (
    AssetUploadCreateView,
    AssetUploadDeleteView,
    AssetUploadlDetailView,
    AssetUploadListView,
    DocumentsView,
    EventListView,
    ExposureRecapitulationView,
    ExposureUploadCreateView,
    ExposureUploadDeleteView,
    ExposureUploadlDetailView,
    ExposureUploadListView,
    HazardListView,
    OpenquakeJobAbortView,
    OpenquakeJobCreateView,
    OpenquakeJobDeleteView,
    OpenquakeJobDetailView,
    OpenquakeJobListView,
    OpenquakeJobRemoveView,
    RiskMatrixDetailView,
    RiskMatrixListView,
    VulnerabilityListView,
)
from ai_risiko.post.views import PostDetailView, PostListView

from .views import (
    index,
    login,
    logout,
    my_profile,
    preferences,
    redirect_to_promoted_post,
)

app_name = "newdashboard"

urlpatterns = [
    path(
        "",
        index,
        name="index",
    ),
    path(
        "login/",
        login,
        name="login",
    ),
    path(
        "logout/",
        logout,
        name="logout",
    ),
    path(
        "redirect-to-promoted-post/",
        redirect_to_promoted_post,
        name="redirect_to_promoted_post",
    ),
    path(
        "my-profile/",
        my_profile,
        name="my_profile",
    ),
    path(
        "preferences/",
        preferences,
        name="preferences",
    ),
    path(
        "hazard-page/",
        login_required(TemplateView.as_view(template_name="newdashboard/hazard.html")),
        name="hazard",
    ),
    path(
        "vulnerability-page/",
        login_required(
            TemplateView.as_view(template_name="newdashboard/vulnerability.html")
        ),
        name="vulnerability",
    ),
    path(
        "about/",
        login_required(TemplateView.as_view(template_name="newdashboard/about.html")),
        name="about",
    ),
    path(
        "calculate/",
        login_required(
            TemplateView.as_view(template_name="newdashboard/calculate.html")
        ),
        name="calculate",
    ),
    path(
        "calculate/hazard/",
        login_required(
            TemplateView.as_view(template_name="newdashboard/calculate-hazard.html")
        ),
        name="calculate_hazard",
    ),
    path("post/", PostListView.as_view(), name="post-list"),
    path("post/<int:pk>/", PostDetailView.as_view(), name="post-detail"),
    # below paths duplicated from dashboard/urls.py
    path("assets/import/", AssetUploadCreateView.as_view(), name="assetupload-create"),
    path("assets/", AssetUploadListView.as_view(), name="assetupload-list"),
    path(
        "assets/<int:pk>/", AssetUploadlDetailView.as_view(), name="assetupload-detail"
    ),
    path(
        "assets/<int:pk>/delete/",
        AssetUploadDeleteView.as_view(),
        name="assetupload-delete",
    ),
    path(
        "exposure/import/",
        ExposureUploadCreateView.as_view(),
        name="exposureupload-create",
    ),
    path("exposure/", ExposureUploadListView.as_view(), name="exposureupload-list"),
    path(
        "exposure/<int:pk>/",
        ExposureUploadlDetailView.as_view(),
        name="exposureupload-detail",
    ),
    path(
        "exposure/<int:pk>/delete/",
        ExposureUploadDeleteView.as_view(),
        name="exposureupload-delete",
    ),
    path(
        "exposure/<int:exposureupload_id>/recapitulation/",
        ExposureRecapitulationView.as_view(),
        name="exposure-recapitulation",
    ),
    path("hazard/", HazardListView.as_view(), name="hazard-list"),
    path("event/", EventListView.as_view(), name="event-list"),
    path("vulnerability/", VulnerabilityListView.as_view(), name="vulnerability-list"),
    path("eq/create/", OpenquakeJobCreateView.as_view(), name="openquakejob-create"),
    path("eq/", OpenquakeJobListView.as_view(), name="openquakejob-list"),
    path("eq/<int:pk>/", OpenquakeJobDetailView.as_view(), name="openquakejob-detail"),
    path(
        "eq/<int:pk>/delete/",
        OpenquakeJobDeleteView.as_view(),
        name="openquakejob-delete",
    ),
    path(
        "eq/<int:pk>/abort/", OpenquakeJobAbortView.as_view(), name="openquakejob-abort"
    ),
    path(
        "eq/<int:pk>/remove/",
        OpenquakeJobRemoveView.as_view(),
        name="openquakejob-remove",
    ),
    path(
        "eq/risk-matrix/",
        RiskMatrixListView.as_view(),
        name="risk-matrix-list",
    ),
    path(
        "eq/<int:openquakejob_id>/risk-matrix/",
        RiskMatrixDetailView.as_view(),
        name="risk-matrix-detail",
    ),
    path(
        "documents/",
        DocumentsView.as_view(),
        name="documents",
    ),
]
