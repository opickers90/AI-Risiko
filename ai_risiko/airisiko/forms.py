import logging

from django import forms
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from .models import AssetUpload, ExposureUpload, OpenquakeJob
from .tasks import import_asset_csv_task, openquake_submit_calc_task


class AssetUploadForm(forms.ModelForm):
    class Meta:
        model = AssetUpload
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        self.dashboard_form = kwargs.pop("dashboard_form", None)
        super().__init__(*args, **kwargs)
        self.fields["csv_delimiter"].initial = ","
        self.fields["csv_column_asset_name"].initial = "name"
        self.fields["csv_column_asset_address"].initial = "address"
        self.fields["csv_column_asset_type"].initial = "type"
        self.fields["csv_column_asset_latitude"].initial = "latitude"
        self.fields["csv_column_asset_longitude"].initial = "longitude"
        self.fields["csv_column_asset_occupancy"].initial = "occupancy"
        # hide fields in dashboard form
        if self.dashboard_form:
            self.fields["name"].required = True
            self.fields["user"].widget = forms.HiddenInput()
            self.fields["import_status"].widget = forms.HiddenInput()
            self.fields["import_message"].widget = forms.HiddenInput()

    def save(
        self, commit=True, force_insert=False, force_update=False, *args, **kwargs
    ):
        created = False
        instance = super().save(commit=False, *args, **kwargs)
        if not instance.id:
            created = True
        if self.user:
            instance.user = self.user
        # save first to write uploaded file
        instance.save()
        # only run task on new creation
        logging.info(f"AssetUploadForm created: {created}")
        if created:
            transaction.on_commit(
                lambda: import_asset_csv_task.delay(upload_id=instance.id)
            )
        return instance


class ExposureUploadForm(forms.ModelForm):
    class Meta:
        model = ExposureUpload
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        self.dashboard_form = kwargs.pop("dashboard_form", None)
        super().__init__(*args, **kwargs)
        self.fields["csv_delimiter"].initial = ","
        self.fields["csv_column_asset_name"].initial = "name"
        # self.fields["csv_column_asset_address"].initial = "address"
        # self.fields["csv_column_asset_type"].initial = "type"
        self.fields["csv_column_asset_latitude"].initial = "lat"
        self.fields["csv_column_asset_longitude"].initial = "lon"
        self.fields["csv_column_asset_occupancy"].initial = "occupancy"
        # extra exposure fields (based on exposure.csv)
        self.fields["csv_column_csv_id"].initial = "id"
        self.fields["csv_column_taxonomy"].initial = "taxonomy"
        self.fields["csv_column_asset_id"].initial = "number"
        self.fields["csv_column_structural"].initial = "structural"
        self.fields["csv_column_night"].initial = "night"
        self.fields["csv_column_material"].initial = "material"
        self.fields["csv_column_llrs"].initial = "llrs"
        self.fields["csv_column_code"].initial = "code"
        self.fields["csv_column_height"].initial = "height"
        self.fields["csv_column_province"].initial = "name_1"
        self.fields["csv_column_city"].initial = "name_2"
        self.fields["csv_column_city_code"].initial = "id_1"
        # self.fields["csv_column_occupancy_description"].initial = "occupancy_desc"
        # self.fields["csv_column_ductility"].initial = "ductility"
        # self.fields["csv_column_group"].initial = "group"
        self.fields["currency_code"].initial = "IDR"
        self.fields["decimal_separator"].initial = ","
        if self.dashboard_form:
            self.fields["name"].required = True
            # below are mandatory columns based from exposure_model.xml
            self.fields["csv_column_asset_name"].required = True
            self.fields["csv_column_asset_latitude"].required = True
            self.fields["csv_column_asset_longitude"].required = True
            self.fields["csv_column_asset_occupancy"].required = True
            self.fields["csv_column_material"].required = True
            self.fields["csv_column_llrs"].required = True
            self.fields["csv_column_code"].required = True
            self.fields["csv_column_height"].required = True
            self.fields["csv_column_province"].required = True
            self.fields["csv_column_city"].required = True
            self.fields["csv_column_city_code"].required = True
            self.fields["user"].widget = forms.HiddenInput()
            self.fields["csv_column_asset_address"].widget = forms.HiddenInput()
            self.fields["csv_column_asset_type"].widget = forms.HiddenInput()
            self.fields["csv_column_occupancy_description"].widget = forms.HiddenInput()
            self.fields["csv_column_ductility"].widget = forms.HiddenInput()
            self.fields["csv_column_group"].widget = forms.HiddenInput()
            self.fields["import_status"].widget = forms.HiddenInput()
            self.fields["import_message"].widget = forms.HiddenInput()

    def save(
        self, commit=True, force_insert=False, force_update=False, *args, **kwargs
    ):
        created = False
        instance = super().save(commit=False, *args, **kwargs)
        if not instance.id:
            created = True
        if self.user:
            instance.user = self.user
        instance.save()
        # only run task on new creation
        logging.info(f"ExposureUploadForm created: {created}")
        if created:
            transaction.on_commit(
                lambda: import_asset_csv_task.delay(
                    upload_id=instance.id, is_exposure=True
                )
            )
        return instance


class OpenquakeJobForm(forms.ModelForm):
    class Meta:
        model = OpenquakeJob
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        self.dashboard_form = kwargs.pop("dashboard_form", None)
        super().__init__(*args, **kwargs)
        if self.dashboard_form:
            self.fields["name"].required = True
            self.fields["calculation_server"].widget = forms.HiddenInput()
            self.fields["user"].widget = forms.HiddenInput()
            self.fields["task_id"].widget = forms.HiddenInput()
            self.fields["task_state"].widget = forms.HiddenInput()
            self.fields["task_start"].widget = forms.HiddenInput()
            self.fields["task_end"].widget = forms.HiddenInput()
            self.fields["job_id"].widget = forms.HiddenInput()
            self.fields["job_status"].widget = forms.HiddenInput()
            self.fields["job_message"].widget = forms.HiddenInput()
            self.fields["job_results"].widget = forms.HiddenInput()
            self.fields["job_results_datastore_file"].widget = forms.HiddenInput()
            self.fields["info"].widget = forms.HiddenInput()
            self.fields["result_files"].widget = forms.HiddenInput()
            # only show openquake job file for superuser
            # exposure is mandatory for non superuser, limit to own exposure data
            if self.user and not self.user.is_superuser:
                self.fields["file"].widget = forms.HiddenInput()
                self.fields["exposure"].required = True
                exposure_qs = self.fields["exposure"].queryset
                self.fields["exposure"].queryset = exposure_qs.filter(
                    exposure_upload__user=self.user
                )

    def clean(self):
        """
        Make sure user submits the exposure data or OpenQuake job archive file.
        """
        exposure = self.cleaned_data.get("exposure", None)
        file = self.cleaned_data.get("file", None)
        if not exposure and not file:
            error_msg = _(
                "Please select an Exposure data or upload an EQ job archive file."
            )
            self.add_error("exposure", error_msg)
            self.add_error("file", error_msg)
        return self.cleaned_data

    def openquake_submit_calc(self, instance):
        res = openquake_submit_calc_task.delay(openquakejob_id=instance.id)
        instance.task_id = res.id
        instance.task_state = res.state
        instance.save()

    def save(
        self, commit=True, force_insert=False, force_update=False, *args, **kwargs
    ):
        created = False
        instance = super().save(commit=False, *args, **kwargs)
        if not instance.id:
            created = True
        if self.user:
            instance.user = self.user
        instance.save()
        # only run task on new creation
        logging.info(f"OpenquakeJobForm created: {created}")
        if created:
            transaction.on_commit(lambda: self.openquake_submit_calc(instance))
        return instance
