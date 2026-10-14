from django.contrib.auth.decorators import login_required
from django.urls import path
from django.views.generic import TemplateView

from .views import (
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
    test_create_openquakejob_from_exposure,
)

app_name = "dashboard"

urlpatterns = [
    path(
        "",
        login_required(TemplateView.as_view(template_name="dashboard/index.html")),
        name="index",
    ),
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
    path("eq/test1/", test_create_openquakejob_from_exposure),
]
