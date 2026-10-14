from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _

from ai_risiko.airisiko.validators import FileSizeValidator, MimetypeValidator

verbose_id = _("ID")
verbose_catatan = _("Catatan")
verbose_nama = _("Nama")
verbose_pulau = _("Pulau")
verbose_provinsi = _("Provinsi")
verbose_kabupaten_kota = _("Kabupaten/Kota")
verbose_kecamatan = _("Kecamatan")
verbose_desa = _("Desa")
verbose_polygon = _("Polygon")
verbose_polygon_small = _("Polygon Small")
verbose_luas = _("Luas")
verbose_geojson = _("GeoJSON")
verbose_geojson_help_text = _(
    'Edit GeoJSON (harus MultiPolygon dan memiliki parameter CRS "CRS84")'
)
verbose_wilayah = _("Wilayah")
verbose_id_kemendagri = _("ID Kemendagri")
verbose_nama_kemendagri = _("Nama Kemendagri")


class Pulau(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name=verbose_id)
    nama = models.CharField(max_length=255, verbose_name=verbose_nama)
    polygon = models.MultiPolygonField(
        null=True, blank=True, verbose_name=verbose_polygon
    )
    polygon_small = models.MultiPolygonField(
        null=True, blank=True, verbose_name=verbose_polygon_small
    )
    luas = models.DecimalField(
        null=True,
        blank=True,
        max_digits=12,
        decimal_places=4,
        help_text=_("dalam kilometer persegi"),
        verbose_name=verbose_luas,
    )
    catatan = models.TextField(blank=True, verbose_name=verbose_catatan)
    geojson = models.FileField(
        null=True,
        blank=True,
        upload_to="administrasiwilayah/pulau/",
        validators=[
            MimetypeValidator(("text/plain", "application/json")),
            FileSizeValidator(1),  # max MB
        ],
        help_text=verbose_geojson_help_text,
        verbose_name=verbose_geojson,
    )

    def __str__(self):
        return self.nama

    class Meta:
        ordering = ["id"]
        get_latest_by = "id"
        verbose_name_plural = _("Pulau")


class Provinsi(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name=verbose_id)
    pulau = models.ForeignKey(
        Pulau,
        models.SET_NULL,
        null=True,
        blank=True,
        related_name="provinsis",
        verbose_name=verbose_pulau,
    )
    nama = models.CharField(max_length=255, verbose_name=verbose_nama)
    polygon = models.MultiPolygonField(
        null=True, blank=True, verbose_name=verbose_polygon
    )
    polygon_small = models.MultiPolygonField(
        null=True, blank=True, verbose_name=verbose_polygon_small
    )
    luas = models.DecimalField(
        null=True,
        blank=True,
        max_digits=12,
        decimal_places=4,
        help_text=_("dalam kilometer persegi"),
        verbose_name=verbose_luas,
    )
    catatan = models.TextField(blank=True, verbose_name=verbose_catatan)
    geojson = models.FileField(
        null=True,
        blank=True,
        upload_to="administrasiwilayah/provinsi/",
        validators=[
            MimetypeValidator(("text/plain", "application/json")),
            FileSizeValidator(1),
        ],
        help_text=verbose_geojson_help_text,
        verbose_name=verbose_geojson,
    )

    def __str__(self):
        return self.nama

    class Meta:
        ordering = ["id"]
        get_latest_by = "id"
        verbose_name_plural = _("Provinsi")


class Kabupaten_Kota(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name=verbose_id)
    provinsi = models.ForeignKey(
        Provinsi, models.SET_NULL, null=True, blank=True, verbose_name=verbose_provinsi
    )
    nama = models.CharField(max_length=255, verbose_name=verbose_nama)
    polygon = models.MultiPolygonField(
        null=True, blank=True, verbose_name=verbose_polygon
    )
    polygon_small = models.MultiPolygonField(
        null=True, blank=True, verbose_name=verbose_polygon_small
    )
    luas = models.DecimalField(
        null=True,
        blank=True,
        max_digits=12,
        decimal_places=4,
        help_text=_("dalam kilometer persegi"),
        verbose_name=verbose_luas,
    )
    catatan = models.TextField(blank=True, verbose_name=verbose_catatan)
    geojson = models.FileField(
        null=True,
        blank=True,
        upload_to="administrasiwilayah/kabupaten_kota/",
        validators=[
            MimetypeValidator(("text/plain", "application/json")),
            FileSizeValidator(1),
        ],
        help_text=verbose_geojson_help_text,
        verbose_name=verbose_geojson,
    )
    id_kemendagri = models.CharField(
        blank=True, max_length=255, verbose_name=verbose_id_kemendagri
    )
    nama_kemendagri = models.CharField(
        blank=True, max_length=255, verbose_name=verbose_nama_kemendagri
    )

    def __str__(self):
        return f"{self.catatan} {self.nama.title()}"

    class Meta:
        ordering = ["id"]
        get_latest_by = "id"
        verbose_name_plural = _("Kabupaten/Kota")


class Kecamatan(models.Model):
    id = models.BigIntegerField(primary_key=True, verbose_name=verbose_id)
    kabupaten_kota = models.ForeignKey(
        Kabupaten_Kota,
        models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=verbose_kabupaten_kota,
    )
    nama = models.CharField(max_length=255, verbose_name=verbose_nama)
    polygon = models.MultiPolygonField(
        null=True, blank=True, verbose_name=verbose_polygon
    )
    polygon_small = models.MultiPolygonField(
        null=True, blank=True, verbose_name=verbose_polygon_small
    )
    luas = models.DecimalField(
        null=True,
        blank=True,
        max_digits=12,
        decimal_places=4,
        help_text=_("dalam kilometer persegi"),
        verbose_name=verbose_luas,
    )
    catatan = models.TextField(blank=True, verbose_name=verbose_catatan)
    geojson = models.FileField(
        null=True,
        blank=True,
        upload_to="administrasiwilayah/kecamatan/",
        validators=[
            MimetypeValidator(("text/plain", "application/json")),
            FileSizeValidator(1),
        ],
        help_text=verbose_geojson_help_text,
        verbose_name=verbose_geojson,
    )
    id_kemendagri = models.CharField(
        blank=True, max_length=255, verbose_name=verbose_id_kemendagri
    )
    nama_kemendagri = models.CharField(
        blank=True, max_length=255, verbose_name=verbose_nama_kemendagri
    )

    def __str__(self):
        return self.nama

    class Meta:
        ordering = ["id"]
        get_latest_by = "id"
        verbose_name_plural = _("Kecamatan")


class Desa(models.Model):
    id = models.BigIntegerField(primary_key=True, verbose_name=verbose_id)
    kecamatan = models.ForeignKey(
        Kecamatan,
        models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=verbose_kecamatan,
    )
    nama = models.CharField(max_length=255, verbose_name=verbose_nama)
    polygon = models.MultiPolygonField(
        null=True, blank=True, verbose_name=verbose_polygon
    )
    polygon_small = models.MultiPolygonField(
        null=True, blank=True, verbose_name=verbose_polygon_small
    )
    luas = models.DecimalField(
        null=True,
        blank=True,
        max_digits=12,
        decimal_places=4,
        help_text=_("dalam kilometer persegi"),
        verbose_name=verbose_luas,
    )
    catatan = models.TextField(blank=True, verbose_name=verbose_catatan)
    geojson = models.FileField(
        null=True,
        blank=True,
        upload_to="administrasiwilayah/desa/",
        validators=[
            MimetypeValidator(("text/plain", "application/json")),
            FileSizeValidator(1),
        ],
        help_text=verbose_geojson_help_text,
        verbose_name=verbose_geojson,
    )
    id_kemendagri = models.CharField(
        blank=True, max_length=255, verbose_name=verbose_id_kemendagri
    )
    nama_kemendagri = models.CharField(
        blank=True, max_length=255, verbose_name=verbose_nama_kemendagri
    )

    def __str__(self):
        return self.nama

    class Meta:
        ordering = ["id"]
        get_latest_by = "id"
        verbose_name_plural = _("Desa")
