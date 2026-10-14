from django.conf import settings
from django.urls import path
from rest_framework.routers import SimpleRouter

from ai_risiko.administrasiwilayah.api.views import (
    KabupatenKotaGeoViewSet,
    KabupatenKotaViewSet,
    KecamatanGeoViewSet,
    KecamatanViewSet,
    ProvinsiGeoViewSet,
    ProvinsiViewSet,
    PulauGeoViewSet,
    PulauViewSet,
)
from ai_risiko.airisiko.api.routers import AiRisikoAPIDefaultRouter
from ai_risiko.airisiko.api.views import (
    EqAbortView,
    EqCreateView,
    EqDeleteView,
    EqRemoveView,
    EqStartView,
    ExposureCreateView,
    ExposureDeleteView,
    calculation_server,
    eq,
    eq_aal,
    eq_elt,
    eq_pml,
    exposure,
    exposure_recapitulation,
    oq_job_details,
)
from ai_risiko.users.api.views import UserViewSet

# from rest_framework.routers import DefaultRouter


if settings.DEBUG:
    # router = DefaultRouter()
    router = AiRisikoAPIDefaultRouter()
else:
    router = SimpleRouter()

router.register("users", UserViewSet)
router.register("pulau", PulauViewSet)
router.register("provinsi", ProvinsiViewSet)
router.register("kabupaten-kota", KabupatenKotaViewSet)
router.register("kecamatan", KecamatanViewSet)
router.register("pulau-geo", PulauGeoViewSet, basename="pulau-geo")
router.register("provinsi-geo", ProvinsiGeoViewSet, basename="provinsi-geo")
router.register(
    "kabupaten-kota-geo", KabupatenKotaGeoViewSet, basename="kabupaten-kota-geo"
)
router.register("kecamatan-geo", KecamatanGeoViewSet, basename="kecamatan-geo")


app_name = "api"
urlpatterns = router.urls

urlpatterns += [
    path(
        "oq_job_details/", oq_job_details, name="oq_job_details"
    ),  # openquakejob details
    path("exposure/", exposure, name="exposure"),
    path("exposure/<int:exposure_id>/", exposure, name="exposure_detail"),
    path(
        "exposure/recapitulation/<int:exposure_id>/",
        exposure_recapitulation,
        name="exposure_recapitulation",
    ),
    path("exposure/create/", ExposureCreateView.as_view(), name="exposure_create"),
    path("exposure/delete/", ExposureDeleteView.as_view(), name="exposure_delete"),
    path("eq/", eq, name="eq"),
    path("eq/<int:openquakejob_id>/", eq, name="eq_detail"),
    path("eq/create/", EqCreateView.as_view(), name="eq_create"),
    path("eq/start/", EqStartView.as_view(), name="eq_start"),
    path("eq/abort/", EqAbortView.as_view(), name="eq_abort"),
    path("eq/remove/", EqRemoveView.as_view(), name="eq_remove"),
    path("eq/delete/", EqDeleteView.as_view(), name="eq_delete"),
    path("eq/aal/<int:openquakejob_id>/", eq_aal, name="eq_aal"),
    path("eq/pml/<int:openquakejob_id>/", eq_pml, name="eq_pml"),
    path("eq/elt/<int:openquakejob_id>/", eq_elt, name="eq_elt"),
    path("calculation-server/", calculation_server, name="calculation_server"),
    path(
        "calculation-server/<int:calculationserver_id>/",
        calculation_server,
        name="calculation_server_detail",
    ),
]
