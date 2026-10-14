from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _

from ai_risiko.administrasiwilayah.models import Kabupaten_Kota, Provinsi
from ai_risiko.airisiko.validators import FileSizeValidator, MimetypeValidator

User = get_user_model()


""" AI Risiko database models.

Database schema reference: https://docs.google.com/presentation/d/1lbYxrrmY1Na6yEN2he7CNI9JpPCaPi_9btivQ4m2kiw/edit#slide=id.g22e45d892e6_0_0  # noqa
"""


class AssetUpload(models.Model):
    """ """

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    name = models.CharField(
        blank=True,
        max_length=255,
        help_text=_("Provide a title about the assets to be imported."),
    )
    user = models.ForeignKey(
        User, models.SET_NULL, related_name="assetuploads", null=True, blank=True
    )
    file = models.FileField(
        upload_to="assetupload/",
        validators=[
            MimetypeValidator(("text/plain", "application/csv", "application/zip")),
            FileSizeValidator(settings.MAX_FILE_UPLOAD_MB),
        ],
        verbose_name=_("CSV file"),
        help_text=_(
            "Uploaded file must be in .csv or .zip format containing a .csv file."
        ),
    )
    csv_delimiter = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("CSV delimiter"),
        help_text=_("The delimiter character between separate values."),
    )
    csv_column_asset_name = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("CSV asset name column header"),
        help_text=_(
            "The column header name in the .csv file to be mapped as asset name."
        ),
    )
    csv_column_asset_address = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("CSV asset address column header"),
        help_text=_(
            "The column header name in the .csv file to be mapped as asset address."
        ),
    )
    csv_column_asset_type = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("CSV asset type column header"),
        help_text=_(
            "The column header name in the .csv file to be mapped as asset type."
        ),
    )
    csv_column_asset_latitude = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("CSV asset latitude column header"),
        help_text=_(
            "The column header name in the .csv file to be mapped as asset latitude coordinate."
        ),
    )
    csv_column_asset_longitude = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("CSV asset longitude column header"),
        help_text=_(
            "The column header name in the .csv file to be mapped as asset longitude coordinate."
        ),
    )
    csv_column_asset_occupancy = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("CSV asset occupancy column header"),
        help_text=_(
            "The column header name in the .csv file to be mapped as asset occupancy."
        ),
    )
    import_status = models.BooleanField(null=True, blank=True)
    import_message = models.TextField(blank=True)

    def __str__(self):
        return (
            f"AssetUpload => ID: {self.id}"
            f" - Name: {self.name}"
            f" - User: {self.user}"
            f" - File: {self.file}"
            f" - CSV delimiter: {self.csv_delimiter}"
            f" - CSV column asset name: {self.csv_column_asset_name}"
            f" - CSV column asset address: {self.csv_column_asset_address}"
            f" - CSV column asset type: {self.csv_column_asset_type}"
            f" - CSV column asset latitude: {self.csv_column_asset_latitude}"
            f" - CSV column asset longitude: {self.csv_column_asset_longitude}"
            f" - CSV column asset occupancy: {self.csv_column_asset_occupancy}"
            f" - Import status: {self.import_status}"
            f" - Import message: {self.import_message}"
        )


class ExposureUpload(models.Model):
    """ """

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    name = models.CharField(
        blank=True,
        max_length=255,
        help_text=_("Provide a title about the exposure to be imported."),
    )
    user = models.ForeignKey(
        User, models.SET_NULL, related_name="exposureuploads", null=True, blank=True
    )
    file = models.FileField(
        upload_to="exposureupload/",
        validators=[
            MimetypeValidator(("text/plain", "application/csv", "application/zip")),
            FileSizeValidator(settings.MAX_FILE_UPLOAD_MB),
        ],
        verbose_name=_("CSV file"),
        help_text=_(
            "Uploaded file must be in .csv or .zip format containing a .csv file."
        ),
    )
    csv_delimiter = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("CSV delimiter"),
        help_text=_("The delimiter character between separate values."),
    )
    csv_column_asset_name = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("CSV asset name column header"),
        help_text=_(
            "The column header name in the .csv file to be mapped as asset name."
        ),
    )
    csv_column_asset_address = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("CSV asset address column header"),
        help_text=_(
            "The column header name in the .csv file to be mapped as asset address."
        ),
    )
    csv_column_asset_type = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("CSV asset type column header"),
        help_text=_(
            "The column header name in the .csv file to be mapped as asset type."
        ),
    )
    csv_column_asset_latitude = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("CSV asset latitude column header"),
        help_text=_(
            "The column header name in the .csv file to be mapped as asset latitude coordinate."
        ),
    )
    csv_column_asset_longitude = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("CSV asset longitude column header"),
        help_text=_(
            "The column header name in the .csv file to be mapped as asset longitude coordinate."
        ),
    )
    csv_column_asset_occupancy = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("CSV asset occupancy column header"),
        help_text=_(
            "The column header name in the .csv file to be mapped as asset occupancy."
        ),
    )
    import_status = models.BooleanField(null=True, blank=True)
    import_message = models.TextField(blank=True)
    # extra exposure fields (based on exposure.csv)
    csv_column_csv_id = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("CSV ID column header"),
        help_text=_("The column header name in the .csv file to be mapped as CSV ID."),
    )
    csv_column_asset_id = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("CSV asset ID column header"),
        help_text=_(
            "The column header name in the .csv file to be mapped as asset ID."
        ),
    )
    csv_column_taxonomy = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("CSV taxonomy column header"),
        help_text=_(
            "The column header name in the .csv file to be mapped as taxonomy."
        ),
    )
    csv_column_structural = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("CSV structural column header"),
        help_text=_(
            "The column header name in the .csv file to be mapped as structural."
        ),
    )
    csv_column_occupancy_description = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("CSV occupancy description column header"),
        help_text=_(
            "The column header name in the .csv file to be mapped as occupancy description."
        ),
    )
    csv_column_city = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("CSV city column header"),
        help_text=_("The column header name in the .csv file to be mapped as city."),
    )
    csv_column_city_code = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("CSV city code column header"),
        help_text=_(
            "The column header name in the .csv file to be mapped as city code."
        ),
    )
    csv_column_province = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("CSV province column header"),
        help_text=_(
            "The column header name in the .csv file to be mapped as province."
        ),
    )
    csv_column_material = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("CSV material column header"),
        help_text=_(
            "The column header name in the .csv file to be mapped as material."
        ),
    )
    csv_column_llrs = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("CSV LLRS column header"),
        help_text=_("The column header name in the .csv file to be mapped as LLRS."),
    )
    csv_column_code = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("CSV code column header"),
        help_text=_("The column header name in the .csv file to be mapped as code."),
    )
    csv_column_ductility = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("CSV ductility column header"),
        help_text=_(
            "The column header name in the .csv file to be mapped as ductility."
        ),
    )
    csv_column_height = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("CSV height column header"),
        help_text=_("The column header name in the .csv file to be mapped as height."),
    )
    csv_column_night = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("CSV night column header"),
        help_text=_("The column header name in the .csv file to be mapped as night."),
    )
    csv_column_group = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("CSV group column header"),
        help_text=_("The column header name in the .csv file to be mapped as group."),
    )
    currency_code = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("Currency code"),
        help_text=_("The currency code based on ISO 4217 (e.g. IDR, USD, SGD)."),
    )
    decimal_separator = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("Decimal separator"),
        help_text=_("The decimal separator character for numeric values."),
    )

    def __str__(self):
        return (
            f"ExposureUpload => ID: {self.id}"
            f" - Name: {self.name}"
            f" - User: {self.user}"
            f" - File: {self.file}"
            f" - CSV delimiter: {self.csv_delimiter}"
            f" - CSV column asset name: {self.csv_column_asset_name}"
            f" - CSV column asset address: {self.csv_column_asset_address}"
            f" - CSV column asset type: {self.csv_column_asset_type}"
            f" - CSV column asset latitude: {self.csv_column_asset_latitude}"
            f" - CSV column asset longitude: {self.csv_column_asset_longitude}"
            f" - CSV column asset occupancy: {self.csv_column_asset_occupancy}"
            f" - Import status: {self.import_status}"
            f" - Import message: {self.import_message}"
        )


class Asset(models.Model):
    """ """

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    asset_upload = models.ForeignKey(
        AssetUpload, models.CASCADE, related_name="assets", null=True, blank=True
    )
    exposure_upload = models.ForeignKey(
        ExposureUpload, models.CASCADE, related_name="assets", null=True, blank=True
    )
    name = models.CharField(blank=True, max_length=255)
    address = models.TextField(blank=True)
    type = models.CharField(blank=True, max_length=255)
    point = models.PointField(null=True, blank=True)
    occupancy = models.CharField(blank=True, max_length=255)  # 202305 update
    kabupaten_kota = models.ForeignKey(
        Kabupaten_Kota, models.SET_NULL, null=True, blank=True
    )  # 202305 update
    bmn = models.CharField(blank=True, max_length=255)
    bmd = models.CharField(blank=True, max_length=255)
    kk = models.CharField(blank=True, max_length=255)
    # extra exposure fields (based on exposure.csv)
    csv_id = models.CharField(blank=True, max_length=255)  # id
    asset_id = models.CharField(blank=True, max_length=255)  # number
    taxonomy = models.CharField(blank=True, max_length=255)  # taxonomy
    structural = models.CharField(blank=True, max_length=255)  # structural
    occupancy_description = models.CharField(blank=True, max_length=255)  # occupancy_desc
    city = models.CharField(blank=True, max_length=255)  # name_2
    city_code = models.CharField(blank=True, max_length=255)  # id_1
    province = models.CharField(blank=True, max_length=255)  # name_1
    material = models.CharField(blank=True, max_length=255)  # material
    llrs = models.CharField(blank=True, max_length=255)  # llrs
    code = models.CharField(blank=True, max_length=255)  # code
    ductility = models.CharField(blank=True, max_length=255)  # ductility
    height = models.CharField(blank=True, max_length=255)  # height
    night = models.CharField(blank=True, max_length=255)  # night
    group = models.CharField(blank=True, max_length=255)  # group

    def __str__(self):
        return (
            f"Asset => ID: {self.id}"
            f" - Name: {self.name}"
            f" - Address: {self.address}"
            f" - Type: {self.type}"
            f" - Point: {self.point}"
            f" - Occupancy: {self.occupancy}"
            f" - Kabupaten_Kota: {self.kabupaten_kota}"
        )


class Exposure(models.Model):
    """ """

    created = models.DateTimeField(auto_now_add=True)  # 202305 update
    updated = models.DateTimeField(auto_now=True)  # 202305 update
    name = models.CharField(blank=True, max_length=255)
    user = models.ForeignKey(
        User, models.SET_NULL, related_name="exposures", null=True, blank=True
    )
    exposure_upload = models.ForeignKey(
        ExposureUpload, models.CASCADE, related_name="exposures", null=True, blank=True
    )
    assets = models.ManyToManyField(Asset, related_name="exposures", blank=True)
    taxonomy = models.CharField(blank=True, max_length=255)
    value = models.FloatField(null=True, blank=True)
    # city = models.CharField(blank=True, max_length=255)  # 202305 update
    # occupancy = models.FloatField(null=True, blank=True)  # 202305 update
    point = models.PointField(null=True, blank=True)

    def __str__(self):
        return (
            f"Exposure => ID: {self.id}"
            f" - Name: {self.name}"
            # f" - Creator: {self.exposure_upload.user}"
        )


class Typology(models.Model):  # 202305 update
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    taxonomy = models.CharField(blank=True, max_length=255)
    disaster = models.CharField(blank=True, max_length=255)
    ratio = models.FloatField(null=True, blank=True)

    def __str__(self):
        return (
            f"Typology => ID {self.id}"
            f" - Taxonomy: {self.taxonomy}"
            f" - Disaster: {self.disaster}"
            f" - Ratio: {self.ratio}"
        )


class Vulnerability(models.Model):
    created = models.DateTimeField(auto_now_add=True)  # 202305 update
    updated = models.DateTimeField(auto_now=True)  # 202305 update
    typology = models.ForeignKey(
        Typology, models.SET_NULL, null=True, blank=True
    )  # 202305 update
    # taxonomy = models.CharField(blank=True, max_length=255)  # 202305 update
    intensity = models.FloatField(null=True, blank=True)
    lr = models.FloatField(null=True, blank=True)

    def __str__(self):
        return (
            f"Vulnerability => ID: {self.id}"
            f" - [Typology: {self.typology}]"
            f" - Intensity: {self.intensity}"
            f" - LR: {self.lr}"
        )

    class Meta:
        verbose_name_plural = "Vulnerabilities"


class Scenario(models.Model):
    created = models.DateTimeField(auto_now_add=True)  # 202305 update
    updated = models.DateTimeField(auto_now=True)  # 202305 update
    prob = models.FloatField(null=True, blank=True)
    rup = models.CharField(blank=True, max_length=255)
    rfl = models.CharField(blank=True, max_length=255)
    erp = models.CharField(blank=True, max_length=255)

    def __str__(self):
        return (
            f"Scenario => ID: {self.id}"
            f" - Prob: {self.prob}"
            f" - RUP: {self.rup}"
            f" - RFL: {self.rfl}"
            f" - EFP: {self.erp}"
        )


class Hazard(models.Model):
    created = models.DateTimeField(auto_now_add=True)  # 202305 update
    updated = models.DateTimeField(auto_now=True)  # 202305 update
    scenario = models.ForeignKey(Scenario, models.SET_NULL, null=True, blank=True)
    # prob = models.FloatField(null=True, blank=True)  # 202305 update
    intensity = models.FloatField(null=True, blank=True)
    disaster = models.CharField(blank=True, max_length=255)
    point = models.PointField(null=True, blank=True)

    def __str__(self):
        return (
            f"Hazard => ID: {self.id}"
            f" - [Scenario: {self.scenario}]"
            f" - Intensity: {self.intensity}"
            f" - Disaster: {self.disaster}"
            f" - Point: {self.point}"
        )


class Risk(models.Model):
    created = models.DateTimeField(auto_now_add=True)  # 202305 update
    updated = models.DateTimeField(auto_now=True)  # 202305 update
    asset = models.ForeignKey(Asset, models.SET_NULL, null=True, blank=True)
    exposure = models.ForeignKey(Exposure, models.SET_NULL, null=True, blank=True)
    hazard = models.ForeignKey(Hazard, models.SET_NULL, null=True, blank=True)
    # event_id = models.CharField(blank=True, max_length=255)  # 202305 update
    # prob = models.FloatField(null=True, blank=True)  # 202305 update
    # intensity = models.FloatField(null=True, blank=True)  # 202305 update
    # disaster = models.CharField(blank=True, max_length=255)  # 202305 update
    lr = models.FloatField(null=True, blank=True)

    def __str__(self):
        return (
            f"Risk => ID: {self.id}"
            f" - [Asset: {self.asset}]"
            f" - [Exposure: {self.exposure}]"
            f" - [Hazard: {self.hazard}]"
            f" - LR: {self.lr}"
        )


class CalculationServer(models.Model):
    """ """

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=255)
    enabled = models.BooleanField(null=True, blank=True)
    type = models.CharField(
        max_length=255,
        help_text=_("For OpenQuake Calculation Server input => openquake"),
    )
    base_url = models.URLField(max_length=200)
    user_login = models.CharField(blank=True, max_length=255)
    user_password = models.CharField(blank=True, max_length=255)
    notes = models.TextField(blank=True)
    status = models.CharField(blank=True, max_length=255)  # "WORKING" if assigned tasks
    active = models.BooleanField(null=True, blank=True)
    last_active = models.DateTimeField(null=True, blank=True)
    last_checked = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return (
            f"CalculationServer => ID: {self.id}"
            f" - Name: {self.name}"
            f" - Base URL: {self.base_url}"
        )


class ResultFile(models.Model):
    """
    Generic model for storing result files.
    """

    name = models.CharField(
        blank=True,
        max_length=255,
        help_text=_("Name describing the file."),
    )
    file = models.FileField(
        null=True,
        blank=True,
        upload_to="results/",
        verbose_name=_("Result file"),
    )

    def __str__(self):
        return (
            f"ResultFile => ID: {self.id}"
            f" - Name: {self.name}"
            f" - File: {self.file}"
            f" - File URL: {self.file.url}"
        )


class OpenquakeJob(models.Model):
    """ """

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    name = models.CharField(
        blank=True,
        max_length=255,
        help_text=_("Provide a title about the Risk Calculation."),
    )
    calculation_server = models.ForeignKey(
        CalculationServer,
        models.SET_NULL,
        related_name="openquakejobs",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        User, models.SET_NULL, related_name="openquakejobs", null=True, blank=True
    )
    exposure = models.ForeignKey(
        Exposure,
        models.SET_NULL,
        related_name="openquakejobs",
        verbose_name=_("Exposure"),
        help_text=_(
            "Select Exposure data to be used for the Risk Calculation. An EQ"
            " job archive file will be generated from the Exposure data."
        ),
        null=True,
        blank=True,
    )
    file = models.FileField(
        upload_to="openquakejob/",
        validators=[
            MimetypeValidator(("application/zip",)),
            FileSizeValidator(settings.MAX_FILE_UPLOAD_MB),
        ],
        verbose_name=_("EQ job archive file"),
        help_text=_("Uploaded file must be in .zip format containing an EQ job."),
        null=True,
        blank=True,
    )
    info = models.TextField(blank=True)
    task_id = models.CharField(blank=True, max_length=255)  # celery
    task_state = models.CharField(blank=True, max_length=255)  # celery
    task_start = models.DateTimeField(null=True, blank=True)  # celery
    task_end = models.DateTimeField(null=True, blank=True)  # celery
    job_id = models.CharField(blank=True, max_length=255)  # openquake
    job_status = models.CharField(blank=True, max_length=255)  # openquake
    job_message = models.TextField(blank=True)  # openquake
    job_results = models.TextField(blank=True)  # openquake
    job_results_datastore_file = models.FileField(  # openquake
        null=True,
        blank=True,
        upload_to="results/",
        verbose_name=_("OpenQuake job datastore result file"),
    )
    result_files = models.ManyToManyField(
        ResultFile,
        related_name="openquakejobs",
        blank=True,
    )

    class Meta:
        verbose_name_plural = _("OpenQuake jobs")

    def __str__(self):
        return (
            f"OpenquakeJob => ID: {self.id}"
            f" - Name: {self.name}"
            f" - User: {self.user}"
            f" - File: {self.file}"
            f" - Job ID: {self.job_id}"
            f" - Job status: {self.job_status}"
        )


class ExposureRecapitulation(models.Model):
    exposure = models.ForeignKey(
        Exposure,
        models.CASCADE,
        related_name="exposurerecapitulations",
        null=True,
        blank=True,
    )
    province = models.CharField(blank=True, max_length=255)
    city = models.CharField(blank=True, max_length=255)
    total = models.DecimalField(  # up to 999999999999999999.99
        null=True,
        blank=True,
        max_digits=20,
        decimal_places=2,
    )

    def __str__(self):
        return (
            f"ExposureRecapitulation => ID: {self.id}"
            f" - Exposure: {self.exposure}"
            f" - Province: {self.province}"
            f" - City: {self.city}"
            f" - Total: {self.total}"
        )

    def is_national(self):
        return self.province == "" and self.city == ""

    def is_province(self):
        return self.province != "" and self.city == ""

    def is_city(self):
        return self.province != "" and self.city != ""


class OpenquakeAAL(models.Model):
    """ """

    openquakejob = models.ForeignKey(
        OpenquakeJob,
        models.CASCADE,
        related_name="openquakeaals",
        null=True,
        blank=True,
    )
    province = models.CharField(blank=True, max_length=255)
    city = models.CharField(blank=True, max_length=255)
    provinsi = models.ForeignKey(Provinsi, models.SET_NULL, null=True, blank=True)
    kabupaten_kota = models.ForeignKey(
        Kabupaten_Kota, models.SET_NULL, null=True, blank=True
    )
    total = models.DecimalField(  # up to 999999999999999999.99
        null=True,
        blank=True,
        max_digits=20,
        decimal_places=2,
    )
    loss_ratio = models.FloatField(null=True, blank=True)  # AALR

    class Meta:
        verbose_name_plural = _("OpenQuake AALs")

    def __str__(self):
        return (
            f"OpenquakeAAL => ID: {self.id}"
            f" - Province: {self.province}"
            f" - City: {self.city}"
            f" - Total: {self.total}"
            f" - Loss ratio (AALR): {self.loss_ratio}"
        )

    def is_national(self):
        return self.province == "" and self.city == ""

    def is_province(self):
        return self.province != "" and self.city == ""

    def is_city(self):
        return self.province != "" and self.city != ""


class OpenquakePML(models.Model):
    """ """

    openquakejob = models.ForeignKey(
        OpenquakeJob,
        models.CASCADE,
        related_name="openquakepmls",
        null=True,
        blank=True,
    )
    return_period = models.IntegerField(null=True, blank=True)
    loss = models.DecimalField(  # up to 999999999999999999.99
        null=True,
        blank=True,
        max_digits=20,
        decimal_places=2,
    )
    loss_ratio = models.FloatField(null=True, blank=True)  # PMLR

    class Meta:
        verbose_name_plural = _("OpenQuake PMLs")

    def __str__(self):
        return (
            f"OpenquakePML => ID: {self.id}"
            f" - Return period: {self.return_period}"
            f" - Loss: {self.loss}"
            f" - Loss ratio (PMLR): {self.loss_ratio}"
        )


class VulnerabilityInformation(models.Model):
    """ """

    class VulnerabilityInformationType(models.TextChoices):
        VULNERABILITY = "VULNERABILITY", _("Vulnerability")
        FRAGILITY = "FRAGILITY", _("Fragility")
        DAMAGE_TO_LOSS = "DAMAGE_TO_LOSS", _("Damage-to-loss")
        CAPACITY = "CAPACITY", _("Capacity")

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    name = models.CharField(
        blank=True,
        max_length=255,
        help_text=_("Provide a name for the vulnerability information."),
    )
    type = models.CharField(
        blank=True,
        max_length=255,
        choices=VulnerabilityInformationType.choices,
        help_text=_("Type of vulnerability information."),
    )
    file_path = models.CharField(
        blank=True,
        max_length=255,
        help_text=_("Provide a path to the vulnerability information file."),
    )

    class Meta:
        verbose_name_plural = _("Vulnerability information")

    def __str__(self):
        return (
            f"VulnerabilityInformation => ID: {self.id}"
            f" - Name: {self.name}"
            f" - Type: {self.type}"
            f" - File path: {self.file_path}"
        )
