from rest_framework import serializers
from rest_framework_gis import serializers as gis_serializers

from ai_risiko.administrasiwilayah.models import (
    Desa,
    Kabupaten_Kota,
    Kecamatan,
    Provinsi,
    Pulau,
)


class PulauSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pulau
        fields = ["id", "nama", "luas", "catatan"]


class ProvinsiSerializer(serializers.ModelSerializer):
    # pulau = PulauSerializer()
    pulau_id = serializers.ReadOnlyField(source="pulau.id")
    pulau_nama = serializers.ReadOnlyField(source="pulau.nama")
    pulau_url = serializers.HyperlinkedRelatedField(
        many=False, read_only=True, view_name="api:pulau-detail", source="pulau.id"
    )

    class Meta:
        model = Provinsi
        fields = [
            "id",
            "pulau_id",
            "pulau_nama",
            "pulau_url",
            "nama",
            "luas",
            "catatan",
        ]


class KabupatenKotaSerializer(serializers.ModelSerializer):
    # provinsi = ProvinsiSerializer()
    provinsi_id = serializers.ReadOnlyField(source="provinsi.id")
    provinsi_nama = serializers.ReadOnlyField(source="provinsi.nama")
    provinsi_url = serializers.HyperlinkedRelatedField(
        many=False,
        read_only=True,
        view_name="api:provinsi-detail",
        source="provinsi.id",
    )

    class Meta:
        model = Kabupaten_Kota
        fields = [
            "id",
            "provinsi_id",
            "provinsi_nama",
            "provinsi_url",
            "nama",
            "luas",
            "catatan",
            "id_kemendagri",
            "nama_kemendagri",
        ]


class KecamatanSerializer(serializers.ModelSerializer):
    # kabupaten_kota = KabupatenKotaSerializer()
    kabupaten_kota_id = serializers.ReadOnlyField(source="kabupaten_kota.id")
    kabupaten_kota_nama = serializers.ReadOnlyField(source="kabupaten_kota.nama")
    kabupaten_kota_url = serializers.HyperlinkedRelatedField(
        many=False,
        read_only=True,
        view_name="api:kabupaten_kota-detail",
        source="kabupaten_kota.id",
    )

    class Meta:
        model = Kecamatan
        fields = [
            "id",
            "kabupaten_kota_id",
            "kabupaten_kota_nama",
            "kabupaten_kota_url",
            "nama",
            "luas",
            "catatan",
            "id_kemendagri",
            "nama_kemendagri",
        ]


class DesaSerializer(serializers.ModelSerializer):
    # kecamatan = KecamatanSerializer()
    kecamatan_id = serializers.ReadOnlyField(source="kecamatan.id")
    kecamatan_nama = serializers.ReadOnlyField(source="kecamatan.nama")
    kecamatan_url = serializers.HyperlinkedRelatedField(
        many=False,
        read_only=True,
        view_name="api:kecamatan-detail",
        source="kecamatan.id",
    )

    class Meta:
        model = Desa
        fields = [
            "id",
            "kecamatan_id",
            "kecamatan_nama",
            "kecamatan_url",
            "nama",
            "luas",
            "catatan",
            "id_kemendagri",
            "nama_kemendagri",
        ]


class PulauGeoSerializer(gis_serializers.GeoFeatureModelSerializer):
    class Meta:
        model = Pulau
        # geo_field = "polygon"
        geo_field = "polygon_small"
        fields = [
            "id",
            "nama",
            "luas",
            "catatan",
        ]


class ProvinsiGeoSerializer(gis_serializers.GeoFeatureModelSerializer):
    pulau_id = serializers.ReadOnlyField(source="pulau.id")
    pulau_nama = serializers.ReadOnlyField(source="pulau.nama")
    pulau_url = serializers.HyperlinkedRelatedField(
        many=False, read_only=True, view_name="api:pulau-detail", source="pulau.id"
    )

    class Meta:
        model = Provinsi
        # geo_field = "polygon"
        geo_field = "polygon_small"
        fields = [
            "id",
            "pulau_id",
            "pulau_nama",
            "pulau_url",
            "nama",
            "luas",
            "catatan",
        ]


class KabupatenKotaGeoSerializer(gis_serializers.GeoFeatureModelSerializer):
    provinsi_id = serializers.ReadOnlyField(source="provinsi.id")
    provinsi_nama = serializers.ReadOnlyField(source="provinsi.nama")
    provinsi_url = serializers.HyperlinkedRelatedField(
        many=False,
        read_only=True,
        view_name="api:provinsi-detail",
        source="provinsi.id",
    )

    class Meta:
        model = Kabupaten_Kota
        # geo_field = "polygon"
        geo_field = "polygon_small"
        fields = [
            "id",
            "provinsi_id",
            "provinsi_nama",
            "provinsi_url",
            "nama",
            "luas",
            "catatan",
            "id_kemendagri",
            "nama_kemendagri",
        ]


class KecamatanGeoSerializer(gis_serializers.GeoFeatureModelSerializer):
    kabupaten_kota_id = serializers.ReadOnlyField(source="kabupaten_kota.id")
    kabupaten_kota_nama = serializers.ReadOnlyField(source="kabupaten_kota.nama")
    kabupaten_kota_url = serializers.HyperlinkedRelatedField(
        many=False,
        read_only=True,
        view_name="api:kabupaten_kota-detail",
        source="kabupaten_kota.id",
    )

    class Meta:
        model = Kecamatan
        # geo_field = "polygon"
        geo_field = "polygon_small"
        fields = [
            "id",
            "kabupaten_kota_id",
            "kabupaten_kota_nama",
            "kabupaten_kota_url",
            "nama",
            "luas",
            "catatan",
            "id_kemendagri",
            "nama_kemendagri",
        ]


class DesaGeoSerializer(gis_serializers.GeoFeatureModelSerializer):
    kecamatan_id = serializers.ReadOnlyField(source="kecamatan.id")
    kecamatan_nama = serializers.ReadOnlyField(source="kecamatan.nama")
    kecamatan_url = serializers.HyperlinkedRelatedField(
        many=False,
        read_only=True,
        view_name="api:kecamatan-detail",
        source="kecamatan.id",
    )

    class Meta:
        model = Desa
        # geo_field = "polygon"
        geo_field = "polygon_small"
        fields = [
            "id",
            "kecamatan_id",
            "kecamatan_nama",
            "kecamatan_url",
            "nama",
            "luas",
            "catatan",
            "id_kemendagri",
            "nama_kemendagri",
        ]
