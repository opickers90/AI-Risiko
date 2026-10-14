from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework_gis.filters import InBBoxFilter

from ai_risiko.administrasiwilayah.filters import (
    DesaFilter,
    KabupatenKotaFilter,
    KecamatanFilter,
    ProvinsiFilter,
)
from ai_risiko.administrasiwilayah.models import (
    Desa,
    Kabupaten_Kota,
    Kecamatan,
    Provinsi,
    Pulau,
)

from .serializers import (
    DesaGeoSerializer,
    DesaSerializer,
    KabupatenKotaGeoSerializer,
    KabupatenKotaSerializer,
    KecamatanGeoSerializer,
    KecamatanSerializer,
    ProvinsiGeoSerializer,
    ProvinsiSerializer,
    PulauGeoSerializer,
    PulauSerializer,
)


class PulauViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read only API endpoint for Pulau.

    Return all for any authenticated user.
    """

    queryset = Pulau.objects.all().defer("polygon", "polygon_small")
    serializer_class = PulauSerializer
    authentication_classes = [TokenAuthentication]


class ProvinsiViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read only API endpoint for Provinsi.

    Return all for any authenticated user.

    Can be filtered by the following query parameters:
      - pulau_id (int)
      - pulau_nama (str)
    """

    queryset = Provinsi.objects.defer("polygon", "polygon_small").select_related(
        "pulau"
    )
    serializer_class = ProvinsiSerializer
    filterset_class = ProvinsiFilter
    authentication_classes = [TokenAuthentication]


class KabupatenKotaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read only API endpoint for Kabupaten_Kota.

    Return all for any authenticated user.

    Can be filtered by the following query parameters:
      - pulau_id (int)
      - pulau_nama (str)
      - provinsi_id (int)
      - provinsi_nama (str)
    """

    queryset = Kabupaten_Kota.objects.defer("polygon", "polygon_small").select_related(
        "provinsi"
    )
    serializer_class = KabupatenKotaSerializer
    filterset_class = KabupatenKotaFilter
    authentication_classes = [TokenAuthentication]


class KecamatanViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read only API endpoint for Kecamatan.

    Return all for any authenticated user.

    Can be filtered by the following query parameters:
      - pulau_id (int)
      - pulau_nama (str)
      - provinsi_id (int)
      - provinsi_nama (str)
      - kabupaten_kota_id (int)
      - kabupaten_kota_nama (str)
    """

    queryset = Kecamatan.objects.defer("polygon", "polygon_small").select_related(
        "kabupaten_kota"
    )
    serializer_class = KecamatanSerializer
    filterset_class = KecamatanFilter
    authentication_classes = [TokenAuthentication]


class DesaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read only API endpoint for Desa.

    Return all for any authenticated user.

    Can be filtered by the following query parameters:
      - pulau_id (int)
      - pulau_nama (str)
      - provinsi_id (int)
      - provinsi_nama (str)
      - kabupaten_kota_id (int)
      - kabupaten_kota_nama (str)
      - kecamatan_id (int)
      - kecamatan_nama (str)
    """

    queryset = Desa.objects.defer("polygon", "polygon_small").select_related(
        "kecamatan"
    )
    serializer_class = DesaSerializer
    filterset_class = DesaFilter
    authentication_classes = [TokenAuthentication]


class PulauGeoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read only Geo API endpoint for Pulau.

    Return all for any authenticated user.
    """

    queryset = Pulau.objects.all()
    serializer_class = PulauGeoSerializer
    # bbox_filter_field = "polygon"
    bbox_filter_field = "polygon_small"
    filter_backends = (InBBoxFilter,)
    authentication_classes = [TokenAuthentication]


class ProvinsiGeoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read only Geo API endpoint for Provinsi.

    Return all for any authenticated user.

    Can be filtered by the following query parameters:
      - pulau_id (int)
      - pulau_nama (str)
    """

    queryset = Provinsi.objects.all()
    serializer_class = ProvinsiGeoSerializer
    # bbox_filter_field = "polygon"
    bbox_filter_field = "polygon_small"
    filter_backends = [InBBoxFilter, DjangoFilterBackend]
    filterset_class = ProvinsiFilter
    authentication_classes = [TokenAuthentication]


class KabupatenKotaGeoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read only Geo API endpoint for Kabupaten_Kota.

    Return all for any authenticated user.

    Can be filtered by the following query parameters:
      - pulau_id (int)
      - pulau_nama (str)
      - provinsi_id (int)
      - provinsi_nama (str)
    """

    queryset = Kabupaten_Kota.objects.select_related("provinsi")
    serializer_class = KabupatenKotaGeoSerializer
    # bbox_filter_field = "polygon"
    bbox_filter_field = "polygon_small"
    filter_backends = [InBBoxFilter, DjangoFilterBackend]
    filterset_class = KabupatenKotaFilter
    authentication_classes = [TokenAuthentication]


class KecamatanGeoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read only Geo API endpoint for Kecamatan.

    Return all for any authenticated user.

    Can be filtered by the following query parameters:
      - pulau_id (int)
      - pulau_nama (str)
      - provinsi_id (int)
      - provinsi_nama (str)
      - kabupaten_kota_id (int)
      - kabupaten_kota_nama (str)
    """

    queryset = Kecamatan.objects.select_related("kabupaten_kota")
    serializer_class = KecamatanGeoSerializer
    # bbox_filter_field = "polygon"
    bbox_filter_field = "polygon_small"
    filter_backends = [InBBoxFilter, DjangoFilterBackend]
    filterset_class = KecamatanFilter
    authentication_classes = [TokenAuthentication]


class DesaGeoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read only Geo API endpoint for Desa.

    Return all for any authenticated user.

    Can be filtered by the following query parameters:
      - pulau_id (int)
      - pulau_nama (str)
      - provinsi_id (int)
      - provinsi_nama (str)
      - kabupaten_kota_id (int)
      - kabupaten_kota_nama (str)
      - kecamatan_id (int)
      - kecamatan_nama (str)
    """

    queryset = Desa.objects.select_related("kecamatan")
    serializer_class = DesaGeoSerializer
    # bbox_filter_field = "polygon"
    bbox_filter_field = "polygon_small"
    filter_backends = [InBBoxFilter, DjangoFilterBackend]
    filterset_class = DesaFilter
    authentication_classes = [TokenAuthentication]
