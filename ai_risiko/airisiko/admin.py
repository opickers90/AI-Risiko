import json
import logging

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.contrib import admin as django_admin
from django.contrib import messages
from django.contrib.gis import admin
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from .forms import AssetUploadForm, ExposureUploadForm, OpenquakeJobForm
from .models import (
    Asset,
    AssetUpload,
    CalculationServer,
    Exposure,
    ExposureRecapitulation,
    ExposureUpload,
    Hazard,
    OpenquakeAAL,
    OpenquakeJob,
    OpenquakePML,
    ResultFile,
    Risk,
    Scenario,
    Vulnerability,
    VulnerabilityInformation,
)
from .tasks import (
    exposure_recapitulate_task,
    mail_admins_task,
    openquake_recapitulate_aal_task,
    openquake_recapitulate_pml_task,
)

admin.site.site_header = "AI Risiko"
admin.site.site_title = "AI Risiko"
# admin.site.index_title = "Site administration"


class CustomGISModelAdmin(admin.GISModelAdmin):
    gis_widget_kwargs = {
        "attrs": {
            "default_zoom": 4,
            "default_lon": 118.630233,  # Indonesia center lon/lat
            "default_lat": -1.378651,
        },
    }


class AssetUploadAdmin(admin.ModelAdmin):
    form = AssetUploadForm
    list_display = [
        "id",
        "name",
        "user",
        "file",
        "csv_delimiter",
        "csv_column_asset_name",
        "csv_column_asset_address",
        "csv_column_asset_type",
        "csv_column_asset_latitude",
        "csv_column_asset_longitude",
        "csv_column_asset_occupancy",
        "import_status",
        "import_message",
    ]
    list_display_links = ["name"]
    list_select_related = ["user"]


class ExposureUploadAdmin(admin.ModelAdmin):
    form = ExposureUploadForm
    list_display = [
        "id",
        "name",
        "user",
        "file",
        "csv_delimiter",
        "csv_column_asset_name",
        "csv_column_asset_address",
        "csv_column_asset_type",
        "csv_column_asset_latitude",
        "csv_column_asset_longitude",
        "csv_column_asset_occupancy",
        "import_status",
        "import_message",
    ]
    list_display_links = ["name"]
    list_select_related = ["user"]


class AssetAdmin(CustomGISModelAdmin):
    list_display = [
        "id",
        "name",
        "created",
        "updated",
        "address",
        "type",
        "point",
        "occupancy",  # 202305 update
        "kabupaten_kota",  # 202305 update
        "bmn",
        "bmd",
        "kk",
    ]
    list_display_links = ["name"]
    list_select_related = ["kabupaten_kota"]


class ExposureAdmin(CustomGISModelAdmin):
    actions = ["exposure_recapitulate"]
    list_display = [
        "id",
        "name",
        "created",  # 202305 update
        "updated",  # 202305 update
    ]
    list_display_links = ["name"]
    exclude = ["assets"]  # maybe large!

    def exposure_recapitulate(self, request, queryset):
        """
        Recapitulate Exposure data to ExposureRecapitulation.
        """
        for obj in queryset:
            exposure_recapitulate_task.delay(exposure_id=obj.id)
        self.message_user(
            request,
            _("The selected exposures are being recapitulated."),
            messages.SUCCESS,
        )

    exposure_recapitulate.short_description = _("Recapitulate selected exposures")


class TypologyAdmin(admin.ModelAdmin):  # 202305 update
    list_display = [
        "id",
        "taxonomy",
        "created",
        "updated",
        "disaster",
        "ratio",
    ]
    list_display_links = ["taxonomy"]


class VulnerabilityAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "typology",  # 202305 update
        "created",  # 202305 update
        "updated",  # 202305 update
        "intensity",
        "lr",
    ]
    list_display_links = ["typology"]


class ScenarioAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "prob",
        "created",  # 202305 update
        "updated",  # 202305 update
        "rup",
        "rfl",
        "erp",
    ]
    list_display_links = ["prob"]


class HazardAdmin(CustomGISModelAdmin):
    list_display = [
        "id",
        "scenario",
        "created",  # 202305 update
        "updated",  # 202305 update
        "intensity",
        "disaster",
        "point",
    ]
    list_display_links = ["scenario"]


class RiskAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "asset",
        "exposure",
        "hazard",  # 202305 update
        "created",  # 202305 update
        "updated",  # 202305 update
        "lr",
    ]
    list_display_links = ["asset"]
    list_select_related = ["asset", "exposure", "hazard"]


class CalculationServerAdmin(admin.ModelAdmin):
    actions = ["calculationserver_start_servers", "calculationserver_stop_servers"]
    list_display = [
        "id",
        "name",
        "enabled",
        "type",
        "base_url",
        "status",
        "active",
        "last_active",
        "last_checked",
    ]
    list_display_links = ["name"]

    def calculationserver_start_servers(self, request, queryset):
        """
        Start Calculation Servers.
        """
        aws_success = False
        aws_error = False
        for obj in queryset:
            if (
                "AWS" in obj.notes
                and settings.EC2_AWS_REGION
                and settings.EC2_AWS_ACCESS_KEY_ID
                and settings.EC2_AWS_SECRET_ACCESS_KEY
            ):
                try:
                    aws_config = json.loads(obj.notes)
                    instance_id = aws_config["AWS"]["instance_id"]
                    ec2 = boto3.client(
                        "ec2",
                        settings.EC2_AWS_REGION,
                        aws_access_key_id=settings.EC2_AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=settings.EC2_AWS_SECRET_ACCESS_KEY,
                    )
                    try:
                        ec2.start_instances(InstanceIds=[instance_id], DryRun=True)
                    except ClientError as e:
                        if "DryRunOperation" not in str(e):
                            logging.error(str(e))
                            aws_error = True
                    # Dry run succeeded, run start_instances without dryrun
                    try:
                        response = ec2.start_instances(
                            InstanceIds=[instance_id], DryRun=False
                        )
                        if response:
                            aws_success = True
                    except ClientError as e:
                        logging.error(e)
                        aws_error = True
                except Exception as err:
                    logging.error(f"ERROR calculationserver_start_servers: {err}")
                    aws_error = True
        if aws_success:
            self.message_user(
                request,
                _("The selected calculation servers are being started."),
                messages.SUCCESS,
            )
            mail_admins_task.delay(
                subject=f'[BACKEND TASK] Started AWS Calculation Server "{obj}"',
                message=f'The calculation server "{obj}" has been started from the Admin backend.',
            )
        if aws_error:
            self.message_user(
                request,
                f"{_('Error starting the calculation server')}: {obj}",
                messages.ERROR,
            )

    calculationserver_start_servers.short_description = _(
        "Start selected calculation servers"
    )

    def calculationserver_stop_servers(self, request, queryset):
        """
        Stop Calculation Servers.
        """
        aws_success = False
        aws_error = False
        for obj in queryset:
            if (
                "AWS" in obj.notes
                and settings.EC2_AWS_REGION
                and settings.EC2_AWS_ACCESS_KEY_ID
                and settings.EC2_AWS_SECRET_ACCESS_KEY
            ):
                try:
                    aws_config = json.loads(obj.notes)
                    instance_id = aws_config["AWS"]["instance_id"]
                    ec2 = boto3.client(
                        "ec2",
                        settings.EC2_AWS_REGION,
                        aws_access_key_id=settings.EC2_AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=settings.EC2_AWS_SECRET_ACCESS_KEY,
                    )
                    try:
                        ec2.stop_instances(InstanceIds=[instance_id], DryRun=True)
                    except ClientError as e:
                        if "DryRunOperation" not in str(e):
                            logging.error(str(e))
                            aws_error = True
                    # Dry run succeeded, run stop_instances without dryrun
                    try:
                        response = ec2.stop_instances(
                            InstanceIds=[instance_id], DryRun=False
                        )
                        if response:
                            aws_success = True
                    except ClientError as e:
                        logging.error(e)
                        aws_error = True
                except Exception as err:
                    logging.error(f"ERROR calculationserver_stop_servers: {err}")
                    aws_error = True
        if aws_success:
            self.message_user(
                request,
                _("The selected calculation servers are being stopped."),
                messages.SUCCESS,
            )
            mail_admins_task.delay(
                subject=f'[BACKEND TASK] Stopped AWS Calculation Server "{obj}"',
                message=f'The calculation server "{obj}" has been stopped from the Admin backend.',
            )
        if aws_error:
            self.message_user(
                request,
                f"{_('Error stopping the calculation server')}: {obj}",
                messages.ERROR,
            )

    calculationserver_stop_servers.short_description = _(
        "Stop selected calculation servers"
    )


class TaskStateFilter(django_admin.SimpleListFilter):
    title = _("Task State")

    parameter_name = "task_state"

    def lookups(self, request, model_admin):
        return [
            ("RECEIVED", _("RECEIVED")),
            ("PENDING", _("PENDING")),
            ("STARTED", _("STARTED")),
            ("RETRY", _("RETRY")),
            ("REVOKED", _("REVOKED")),
            ("SUCCESS", _("SUCCESS")),
            ("FAILURE", _("FAILURE")),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(task_state=self.value())
        return queryset


class JobStatusFilter(django_admin.SimpleListFilter):
    title = _("Job Status")

    parameter_name = "job_status"

    def lookups(self, request, model_admin):
        return [
            ("created", _("Created")),
            ("submitted", _("Submitted")),
            ("executing", _("Executing")),
            ("complete", _("Complete")),
            ("aborted", _("Aborted")),
            ("failed", _("Failed")),
            ("deleted", _("Deleted")),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(job_status=self.value())
        return queryset


class OpenquakeJobAdmin(admin.ModelAdmin):
    form = OpenquakeJobForm
    actions = ["openquakejob_recapitulate_aal", "openquakejob_recapitulate_pml"]
    list_display = [
        "id",
        "name",
        "calculation_server",
        "user",
        "file",
        "task_id",
        "task_state",
        "task_start",
        "task_end",
        "job_id",
        "job_status",
        "info",
    ]
    list_select_related = ["calculation_server", "user"]
    list_display_links = ["name"]
    list_filter = [TaskStateFilter, JobStatusFilter]
    search_fields = [
        "name",
        "calculation_server__name",
        "user__username",
        "task_state",
        "job_id",
        "job_status",
        "info"
    ]

    def openquakejob_recapitulate_aal(self, request, queryset):
        """
        Recapitulate Average Asset Losses Statistics zipped .csv from an OpenquakeJob to OpenquakeAAL.
        """
        recap = False
        for obj in queryset:
            if obj.task_state == "SUCCESS" and obj.job_status == "complete":
                openquake_recapitulate_aal_task.delay(openquakejob_id=obj.id)
                recap = True
        if recap:
            self.message_user(
                request,
                _("The AAL for the selected OpenQuake jobs are being recapitulated."),
                messages.SUCCESS,
            )

    openquakejob_recapitulate_aal.short_description = _(
        "Recapitulate AAL for selected OpenQuake jobs"
    )

    def openquakejob_recapitulate_pml(self, request, queryset):
        """
        Recapitulate Aggregate Risk Curves Statistics .csv from an OpenquakeJob to OpenquakePML.
        """
        recap = False
        for obj in queryset:
            if obj.task_state == "SUCCESS" and obj.job_status == "complete":
                openquake_recapitulate_pml_task.delay(openquakejob_id=obj.id)
                recap = True
        if recap:
            self.message_user(
                request,
                _("The PML for the selected OpenQuake jobs are being recapitulated."),
                messages.SUCCESS,
            )

    openquakejob_recapitulate_pml.short_description = _(
        "Recapitulate PML for selected OpenQuake jobs"
    )


class ResultFileAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "name",
        "file",
    ]
    list_display_links = ["name"]


class LevelListFilter(django_admin.SimpleListFilter):
    title = _("Level")

    parameter_name = "level"

    def lookups(self, request, model_admin):
        return [
            ("national", _("National")),
            ("province", _("Province")),
            ("city", _("City")),
        ]

    def queryset(self, request, queryset):
        if self.value() == "national":
            return queryset.filter(province="", city="")
        if self.value() == "province":
            return queryset.filter(~Q(province=""), city="")
        if self.value() == "city":
            return queryset.filter(~Q(province=""), ~Q(city=""))
        return queryset


class ExposureRecapitulationAdmin(django_admin.ModelAdmin):
    list_display = [
        "id",
        "exposure",
        "province",
        "city",
        "total",
    ]
    list_display_links = ["exposure"]
    list_select_related = ["exposure"]
    list_filter = [LevelListFilter]
    search_fields = ["exposure__id", "exposure__name", "province", "city"]


class OpenquakePMLAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "openquakejob",
        "return_period",
        "loss",
        "loss_ratio",
    ]
    list_display_links = ["openquakejob"]
    list_select_related = ["openquakejob"]
    search_fields = ["openquakejob__id", "openquakejob__name"]


class OpenquakeAALAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "openquakejob",
        "province",
        "city",
        "provinsi",
        "kabupaten_kota",
        "total",
        "loss_ratio",
    ]
    list_display_links = ["openquakejob"]
    list_select_related = ["openquakejob", "provinsi", "kabupaten_kota"]
    list_filter = [LevelListFilter]
    search_fields = ["openquakejob__id", "openquakejob__name", "province", "city"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.defer(
            "provinsi__polygon",
            "provinsi__polygon_small",
            "provinsi__pulau__polygon",
            "provinsi__pulau__polygon_small",
            "kabupaten_kota__polygon",
            "kabupaten_kota__polygon_small",
            "kabupaten_kota__provinsi__polygon",
            "kabupaten_kota__provinsi__polygon_small",
            "kabupaten_kota__provinsi__pulau__polygon",
            "kabupaten_kota__provinsi__pulau__polygon_small",
        )


class VulnerabilityInformationAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "name",
        "file_path",
        "type",
    ]
    list_display_links = ["name"]
    list_filter = ["type"]
    search_fields = ["name", "file_path", "type"]


# custom model admin ordering
ADMIN_ORDERING = {
    "administrasiwilayah": [
        "Pulau",
        "Provinsi",
        "Kabupaten_Kota",
        "Kecamatan",
    ],
}


def get_app_list(self, request, app_label=None):
    """
    Return a sorted list of all the installed apps that have been
    registered in this site.
    """
    app_dict = self._build_app_dict(request, app_label)
    # keep apps sorted alphabetically
    app_list = sorted(app_dict.values(), key=lambda x: x["name"].lower())
    for app in app_list:
        # but sort model admins by custom ordering
        if app["app_label"] in ADMIN_ORDERING:
            app["models"].sort(
                key=lambda x: ADMIN_ORDERING[app["app_label"]].index(x["object_name"])
            )
        else:
            app["models"].sort(key=lambda x: x["name"])
    return app_list


# override default admin site ordering
admin.AdminSite.get_app_list = get_app_list

admin.site.register(AssetUpload, AssetUploadAdmin)
admin.site.register(ExposureUpload, ExposureUploadAdmin)
admin.site.register(Asset, AssetAdmin)
admin.site.register(Exposure, ExposureAdmin)
admin.site.register(Vulnerability, VulnerabilityAdmin)
admin.site.register(Scenario, ScenarioAdmin)
admin.site.register(Hazard, HazardAdmin)
admin.site.register(Risk, RiskAdmin)
admin.site.register(OpenquakeJob, OpenquakeJobAdmin)
admin.site.register(CalculationServer, CalculationServerAdmin)
admin.site.register(ResultFile, ResultFileAdmin)
admin.site.register(ExposureRecapitulation, ExposureRecapitulationAdmin)
admin.site.register(OpenquakePML, OpenquakePMLAdmin)
admin.site.register(OpenquakeAAL, OpenquakeAALAdmin)
admin.site.register(VulnerabilityInformation, VulnerabilityInformationAdmin)
