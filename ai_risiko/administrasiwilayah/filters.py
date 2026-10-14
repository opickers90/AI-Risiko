from django_filters import rest_framework as filters

from .models import Desa, Kabupaten_Kota, Kecamatan, Provinsi


class ProvinsiFilter(filters.FilterSet):
    pulau_id = filters.CharFilter(field_name="pulau__id")
    pulau_nama = filters.CharFilter(field_name="pulau__nama", lookup_expr="icontains")

    class Meta:
        model = Provinsi
        fields = ["pulau_id", "pulau_nama"]


class KabupatenKotaFilter(filters.FilterSet):
    pulau_id = filters.CharFilter(field_name="provinsi__pulau__id")
    pulau_nama = filters.CharFilter(
        field_name="provinsi__pulau__nama", lookup_expr="icontains"
    )
    provinsi_id = filters.CharFilter(field_name="provinsi__id")
    provinsi_nama = filters.CharFilter(
        field_name="provinsi__nama", lookup_expr="icontains"
    )

    class Meta:
        model = Kabupaten_Kota
        fields = ["pulau_id", "pulau_nama", "provinsi_id", "provinsi_nama"]


class KecamatanFilter(filters.FilterSet):
    pulau_id = filters.CharFilter(field_name="kabupaten_kota__provinsi__pulau__id")
    pulau_nama = filters.CharFilter(
        field_name="kabupaten_kota__provinsi__pulau__nama", lookup_expr="icontains"
    )
    provinsi_id = filters.CharFilter(field_name="kabupaten_kota__provinsi__id")
    provinsi_nama = filters.CharFilter(
        field_name="kabupaten_kota__provinsi__nama", lookup_expr="icontains"
    )
    kabupaten_kota_id = filters.CharFilter(field_name="kabupaten_kota__id")
    kabupaten_kota_nama = filters.CharFilter(
        field_name="kabupaten_kota__nama", lookup_expr="icontains"
    )

    class Meta:
        model = Kecamatan
        fields = [
            "pulau_id",
            "pulau_nama",
            "provinsi_id",
            "provinsi_nama",
            "kabupaten_kota_id",
            "kabupaten_kota_nama",
        ]


class DesaFilter(filters.FilterSet):
    pulau_id = filters.CharFilter(
        field_name="kecamatan__kabupaten_kota__provinsi__pulau__id"
    )
    pulau_nama = filters.CharFilter(
        field_name="kecamatan__kabupaten_kota__provinsi__pulau__nama",
        lookup_expr="icontains",
    )
    provinsi_id = filters.CharFilter(
        field_name="kecamatan__kabupaten_kota__provinsi__id"
    )
    provinsi_nama = filters.CharFilter(
        field_name="kecamatan__kabupaten_kota__provinsi__nama", lookup_expr="icontains"
    )
    kabupaten_kota_id = filters.CharFilter(field_name="kecamatan__kabupaten_kota__id")
    kabupaten_kota_nama = filters.CharFilter(
        field_name="kecamatan__kabupaten_kota__nama", lookup_expr="icontains"
    )
    kecamatan_id = filters.CharFilter(field_name="kecamatan__id")
    kecamatan_nama = filters.CharFilter(
        field_name="kecamatan__nama", lookup_expr="icontains"
    )

    class Meta:
        model = Desa
        fields = [
            "pulau_id",
            "pulau_nama",
            "provinsi_id",
            "provinsi_nama",
            "kabupaten_kota_id",
            "kabupaten_kota_nama",
            "kecamatan_id",
            "kecamatan_nama",
        ]
