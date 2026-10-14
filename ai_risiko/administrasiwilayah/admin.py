import json
import os

from django.contrib.admin import SimpleListFilter
from django.contrib.gis import admin
from django.utils.translation import gettext_lazy as _
from leaflet.admin import LeafletGeoAdmin
from related_admin import RelatedFieldAdmin, getter_for_related_field

from .models import Kabupaten_Kota, Kecamatan, Provinsi, Pulau

# from .models import Desa


verbose_pulau_details = _("Pulau")
verbose_provinsi_details = _("Provinsi")
verbose_kabupaten_kota_details = _("Kabupaten/Kota")
verbose_kecamatan_details = _("Kecamatan")
verbose_desa_details = _("Desa")
verbose_kecamatan_details = _("Kecamatan")


class GeolevelsAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        """
        Replace Geolevel multipolygon with uploaded .geojson CRS84 file.
        Delete the .geojson file after updating the multipolygon.
        """
        obj.save()
        if obj.geojson:
            with open(obj.geojson.path) as f:
                geojson = json.load(f)
                f.close()
                if "features" in geojson and "crs" in geojson:
                    crs = geojson["crs"]["properties"]["name"]
                    if "CRS84" in crs:
                        for feature in geojson["features"]:
                            if feature["geometry"]["type"] == "MultiPolygon":
                                geometry = feature["geometry"]
                                if geometry:
                                    obj.polygon = json.dumps(geometry)
            try:
                os.remove(obj.geojson.path)
            except FileNotFoundError:
                raise FileNotFoundError(_("File GeoJSON tidak ditemukan."))
            obj.geojson = None
            obj.save()


class PulauFilter(SimpleListFilter):
    """
    Custom filter by pulau since requesting polygon fields causes super slow queries.
    """

    title = _("Pulau")
    parameter_name = "pulau"

    def lookups(self, request, model_admin):
        pulaus = Pulau.objects.all().defer("polygon", "polygon_small")
        return [(pulau.id, pulau.nama) for pulau in pulaus]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(pulau__id__exact=self.value())
        else:
            return queryset


class PulauAdmin(RelatedFieldAdmin, LeafletGeoAdmin, GeolevelsAdmin):
    fieldsets = [
        (
            verbose_pulau_details,
            {
                "fields": [
                    "id",
                    "nama",
                    "polygon",
                    "polygon_small",
                    "geojson",
                    "luas",
                    "catatan",
                ]
            },
        )
    ]
    list_display = [
        "id",
        "nama",
        "luas",
    ]
    list_display_links = ("nama",)
    search_fields = ["nama"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.defer("polygon", "polygon_small")


class ProvinsiFilter(SimpleListFilter):
    """
    Custom filter by provinsi since requesting polygon fields causes super slow queries.
    """

    title = _("Provinsi")
    parameter_name = "provinsi"

    def lookups(self, request, model_admin):
        provinsis = Provinsi.objects.all().defer("polygon", "polygon_small")
        return [(provinsi.id, provinsi.nama) for provinsi in provinsis]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(provinsi__id__exact=self.value())
        else:
            return queryset


class ProvinceFilter(SimpleListFilter):
    """
    Based on ProvinsiFilter.
    """

    title = _("Provinsi")
    parameter_name = "province"

    def lookups(self, request, model_admin):
        provinsis = Provinsi.objects.all().defer("polygon", "polygon_small")
        return [(provinsi.id, provinsi.nama) for provinsi in provinsis]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(province__id__exact=self.value())
        else:
            return queryset


class ProvinsiAdmin(RelatedFieldAdmin, LeafletGeoAdmin, GeolevelsAdmin):
    fieldsets = [
        (
            verbose_provinsi_details,
            {
                "fields": [
                    "id",
                    "pulau",
                    "nama",
                    "polygon",
                    "polygon_small",
                    "geojson",
                    "luas",
                    "catatan",
                ]
            },
        )
    ]
    list_display = [
        "id",
        "sort_pulau_by_name",
        "nama",
        "luas",
    ]
    list_display_links = ["nama"]
    list_select_related = ["pulau"]
    list_filter = [PulauFilter]
    search_fields = ["nama", "pulau__nama"]

    sort_pulau_by_name = getter_for_related_field(
        "pulau", admin_order_field="pulau__nama"
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.defer(
            "polygon", "polygon_small", "pulau__polygon", "pulau__polygon_small"
        )


class KabupatenKotaFilter(SimpleListFilter):
    """
    Custom filter by kabupaten/kota since requesting polygon fields causes super slow queries.
    """

    title = _("Kabupaten/Kota")
    parameter_name = "kabupaten_kota"

    def lookups(self, request, model_admin):
        kabupaten_kotas = Kabupaten_Kota.objects.all().defer("polygon", "polygon_small")
        return [
            (kabupaten_kota.id, kabupaten_kota.nama)
            for kabupaten_kota in kabupaten_kotas
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(kabupaten_kota__id__exact=self.value())
        else:
            return queryset


class KabupatenKotaAdmin(RelatedFieldAdmin, LeafletGeoAdmin, GeolevelsAdmin):
    fieldsets = [
        (
            verbose_kabupaten_kota_details,
            {
                "fields": [
                    "id",
                    "provinsi",
                    "nama",
                    "polygon",
                    "polygon_small",
                    "geojson",
                    "luas",
                    "catatan",
                    "id_kemendagri",
                    "nama_kemendagri",
                ]
            },
        )
    ]
    list_display = [
        "id",
        "sort_pulau_by_name",
        "sort_provinsi_by_name",
        "nama",
        "luas",
        "id_kemendagri",
        "nama_kemendagri",
    ]
    list_display_links = ["nama"]
    list_select_related = ["provinsi", "provinsi__pulau"]
    list_filter = [ProvinsiFilter]
    search_fields = ["nama", "provinsi__nama", "provinsi__pulau__nama"]

    sort_pulau_by_name = getter_for_related_field(
        "provinsi__pulau",
        admin_order_field="provinsi__pulau__nama",
        short_description=_("Pulau"),
    )

    sort_provinsi_by_name = getter_for_related_field(
        "provinsi", admin_order_field="provinsi__nama"
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.defer(
            "polygon",
            "polygon_small",
            "provinsi__polygon",
            "provinsi__polygon_small",
            "provinsi__pulau__polygon",
            "provinsi__pulau__polygon_small",
        )


class KecamatanFilter(SimpleListFilter):
    """
    Custom filter by kecamatan since requesting polygon fields causes super slow queries.
    """

    title = _("Kecamatan")
    parameter_name = "kecamatan"

    def lookups(self, request, model_admin):
        kecamatans = Kecamatan.objects.all().defer("polygon", "polygon_small")
        return [(kecamatan.id, kecamatan.nama) for kecamatan in kecamatans]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(kecamatan__id__exact=self.value())
        else:
            return queryset


class KecamatanAdmin(RelatedFieldAdmin, LeafletGeoAdmin, GeolevelsAdmin):
    fieldsets = [
        (
            verbose_desa_details,
            {
                "fields": [
                    "id",
                    "kabupaten_kota",
                    "nama",
                    "polygon",
                    "polygon_small",
                    "geojson",
                    "luas",
                    "catatan",
                    "id_kemendagri",
                    "nama_kemendagri",
                ]
            },
        )
    ]
    list_display = [
        "id",
        "sort_pulau_by_name",
        "sort_provinsi_by_name",
        "sort_kabupaten_kota_by_name",
        "nama",
        "luas",
        "id_kemendagri",
        "nama_kemendagri",
    ]
    list_display_links = ["nama"]
    list_select_related = ["kabupaten_kota", "kabupaten_kota__provinsi", "kabupaten_kota__provinsi__pulau"]
    list_filter = [KabupatenKotaFilter]
    search_fields = [
        "nama",
        "kabupaten_kota__provinsi__pulau__nama",
        "kabupaten_kota__provinsi__nama",
        "kabupaten_kota__nama",
    ]

    sort_pulau_by_name = getter_for_related_field(
        "kabupaten_kota__provinsi__pulau",
        admin_order_field="kabupaten_kota__provinsi__pulau__nama",
        short_description=_("Pulau"),
    )

    sort_provinsi_by_name = getter_for_related_field(
        "kabupaten_kota__provinsi",
        admin_order_field="kabupaten_kota__provinsi__nama",
        short_description=_("Provinsi"),
    )

    sort_kabupaten_kota_by_name = getter_for_related_field(
        "kabupaten_kota", admin_order_field="kabupaten_kota__nama"
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.defer(
            "polygon",
            "polygon_small",
            "kabupaten_kota__polygon",
            "kabupaten_kota__polygon_small",
            "kabupaten_kota__provinsi__polygon",
            "kabupaten_kota__provinsi__polygon_small",
            "kabupaten_kota__provinsi__pulau__polygon",
            "kabupaten_kota__provinsi__pulau__polygon_small",
        )


"""
class DesaAdmin(RelatedFieldAdmin, LeafletGeoAdmin, GeolevelsAdmin):
    fieldsets = [
        (
            verbose_desa_details,
            {
                "fields": [
                    "id",
                    "kecamatan",
                    "nama",
                    "polygon",
                    "polygon_small",
                    "geojson",
                    "luas",
                    "catatan",
                    "id_kemendagri",
                    "nama_kemendagri",
                ]
            },
        )
    ]
    list_display = [
        "id",
        "sort_pulau_by_name",
        "sort_provinsi_by_name",
        "sort_kabupaten_kota_by_name",
        "sort_kecamatan_kota_by_name",
        "nama",
        "luas",
        "id_kemendagri",
        "nama_kemendagri",
    ]
    list_display_links = ("nama",)
    list_filter = [
        "kecamatan__kabupaten_kota__provinsi__pulau__nama",
        "kecamatan__kabupaten_kota__provinsi__nama",
    ]
    search_fields = [
        "nama",
        "kecamatan__nama",
        "kecamatan__kabupaten_kota__provinsi__pulau__nama",
        "kecamatan__kabupaten_kota__provinsi__nama",
        "kecamatan__kabupaten_kota__nama",
    ]

    sort_pulau_by_name = getter_for_related_field(
        "kecamatan__kabupaten_kota__provinsi__pulau",
        admin_order_field="kecamatan__kabupaten_kota__provinsi__pulau__nama",
        short_description=_("Pulau"),
    )

    sort_provinsi_by_name = getter_for_related_field(
        "kecamatan__kabupaten_kota__provinsi",
        admin_order_field="kecamatan__kabupaten_kota__provinsi__nama",
        short_description=_("Provinsi"),
    )

    sort_kabupaten_kota_by_name = getter_for_related_field(
        "kecamatan__kabupaten_kota",
        admin_order_field="kecamatan__kabupaten_kota__nama",
        short_description=_("Kabupaten Kota"),
    )
    sort_kecamatan_kota_by_name = getter_for_related_field(
        "kecamatan", admin_order_field="kecamatan__nama"
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.defer(
            "polygon",
            "polygon_small",
            "kecamatan__polygon",
            "kecamatan__polygon_small",
            "kecamatan__kabupaten_kota__polygon",
            "kecamatan__kabupaten_kota__polygon_small",
            "kecamatan__kabupaten_kota__provinsi__polygon",
            "kecamatan__kabupaten_kota__provinsi__polygon_small",
            "kecamatan__kabupaten_kota__provinsi__pulau__polygon",
            "kecamatan__kabupaten_kota__provinsi__pulau__polygon_small",
        )
"""


admin.site.register(Pulau, PulauAdmin)
admin.site.register(Provinsi, ProvinsiAdmin)
admin.site.register(Kabupaten_Kota, KabupatenKotaAdmin)
admin.site.register(Kecamatan, KecamatanAdmin)
# admin.site.register(Desa, DesaAdmin)
