import io
import json
import logging
import os
import zipfile
from datetime import datetime

from constance import config as constance_config
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core import files
from django.core.files.base import ContentFile
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
)

from ai_risiko.administrasiwilayah.models import Provinsi  # noqa
from ai_risiko.airisiko.forms import (
    AssetUploadForm,
    ExposureUploadForm,
    OpenquakeJobForm,
)
from ai_risiko.airisiko.models import (
    AssetUpload,
    ExposureRecapitulation,
    ExposureUpload,
    OpenquakeAAL,
    OpenquakeJob,
    OpenquakePML,
    VulnerabilityInformation,
)
from ai_risiko.airisiko.tasks import (
    exposureupload_delete_task,
    openquake_abort_calc_task,
    openquake_remove_calc_task,
    openquake_submit_calc_task,
)
from ai_risiko.airisiko.templatetags.airisiko_tags import (
    airisiko_check_active_calculation_server,
)

msg_no_access = _("Access forbidden.")
msg_job_period = (
    f'{_("Risk Calculation job is only available from")}:'
    f" {constance_config.OPENQUAKE_JOB_PERIOD_START} - {constance_config.OPENQUAKE_JOB_PERIOD_END}"
)
msg_job_stopped = _("Risk Calculation job is being stopped.")
msg_job_stop_failed = _("Failed to stop Risk Calculation job.")
msg_job_removed = _("Risk Calculation job is being removed.")
msg_job_remove_failed = _("Failed to remove Risk Calculation job.")
msg_job_quota_reached = _(
    "Cannot create new Risk Calculation job. You have reached your quota"
)
msg_job_cannot_delete_completed = _("Cannot delete completed Risk Calculation job.")
msg_job_cannot_abort = _("Cannot abort Risk Calculation job.")
msg_job_cannot_remove = _("Cannot remove Risk Calculation job.")


def user_is_superuser_analyst_developer(user):
    """
    Check if user is Superuser, Analyst, or Developer.
    """
    result = False
    if user.is_superuser:
        result = True
    elif user.groups.filter(name="Analyst").exists():
        result = True
    elif user.groups.filter(name="Developer").exists():
        result = True
    return result


def user_is_superuser_or_in_groups(user, groups):
    """
    Check if user is Superuser or belong in specified groups.
    """
    result = False
    if user.is_superuser:
        result = True
    user_groups = list(user.groups.values_list("name", flat=True))
    for group in groups:
        if group in user_groups:
            result = True
            break
    return result


class AssetUploadCreateView(LoginRequiredMixin, CreateView):
    template_name = "dashboard/assetupload_create.html"
    model = AssetUpload
    form_class = AssetUploadForm
    success_url = reverse_lazy("newdashboard:assetupload-list")
    success_message = _("Asset upload in progress, please wait and refresh this page.")

    def dispatch(self, request, *args, **kwargs):
        """
        User must belong to the Analyst group.
        Superuser can access all.
        """
        if not user_is_superuser_or_in_groups(self.request.user, ["Analyst"]):
            messages.error(self.request, msg_no_access)
            return redirect("dashboard:index")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.object = None
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        return self.render_to_response(self.get_context_data(form=form))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"create": True})
        if self.request.path == reverse("newdashboard:assetupload-create"):
            self.template_name = "newdashboard/assetupload_create.html"
        return context

    def get_form_kwargs(self):
        """
        Pass the current user to the form.
        """
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user, "dashboard_form": True})
        return kwargs

    def post(self, request, *args, **kwargs):
        self.object = None
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, self.success_message)
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        for error, message in form.errors.items():
            err = error.replace("_", " ").title()
            msg = message.as_text().replace("*", "")
            error_message = f"{err}: {msg}"
            messages.error(self.request, error_message)
        return self.render_to_response(self.get_context_data(form=form))


class AssetUploadListView(LoginRequiredMixin, ListView):
    template_name = "dashboard/assetupload_list.html"
    model = AssetUpload

    def get_queryset(self):
        """
        Return user's AssetUploads.
        Superuser can access all.
        """
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            qs = qs.filter(user=self.request.user)
        qs = qs.order_by("-id")
        return qs

    def dispatch(self, request, *args, **kwargs):
        """
        User must belong to the Analyst group.
        Superuser can access all.
        """
        if not user_is_superuser_or_in_groups(self.request.user, ["Analyst"]):
            messages.error(self.request, msg_no_access)
            return redirect("dashboard:index")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.path == reverse("newdashboard:assetupload-list"):
            self.template_name = "newdashboard/assetupload_list.html"
        return context


class AssetUploadlDetailView(LoginRequiredMixin, DetailView):
    template_name = "dashboard/assetupload_detail.html"
    model = AssetUpload

    def dispatch(self, request, *args, **kwargs):
        """
        User must belong to the Analyst group.
        Superuser can access all.
        """
        instance = self.get_object()
        user_can_access = user_is_superuser_or_in_groups(self.request.user, ["Analyst"])
        # for non superuser, check if instance belongs to user
        if not self.request.user.is_superuser:
            if instance.user == self.request.user:
                user_can_access = True
            else:
                user_can_access = False
        if not user_can_access:
            messages.error(self.request, msg_no_access)
            return redirect("dashboard:index")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # assetupload = self.object
        if self.request.path == reverse(
            "newdashboard:assetupload-detail", kwargs={"pk": self.object.id}
        ):
            self.template_name = "newdashboard/assetupload_detail.html"
        return context


class AssetUploadDeleteView(LoginRequiredMixin, DeleteView):
    template_name = "dashboard/assetupload_delete.html"
    model = AssetUpload
    success_url = reverse_lazy("newdashboard:assetupload-list")
    success_message = _("Asset upload successfully deleted.")

    def dispatch(self, request, *args, **kwargs):
        """
        User must belong to the Analyst group.
        Superuser can access all.
        """
        instance = self.get_object()
        user_can_access = user_is_superuser_or_in_groups(self.request.user, ["Analyst"])
        # for non superuser, check if instance belongs to user
        if not self.request.user.is_superuser:
            if instance.user == self.request.user:
                user_can_access = True
            else:
                user_can_access = False
        if not user_can_access:
            messages.error(self.request, msg_no_access)
            return redirect("dashboard:index")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        messages.success(self.request, self.success_message)
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.path == reverse(
            "newdashboard:assetupload-delete", kwargs={"pk": self.object.id}
        ):
            self.template_name = "newdashboard/assetupload_delete.html"
        return context


class ExposureUploadCreateView(LoginRequiredMixin, CreateView):
    template_name = "dashboard/exposureupload_create.html"
    model = ExposureUpload
    form_class = ExposureUploadForm
    success_url = reverse_lazy("newdashboard:exposureupload-list")
    success_message = _(
        "Exposure upload in progress, please wait and refresh this page."
    )

    def dispatch(self, request, *args, **kwargs):
        """
        User must belong to the Analyst group.
        Superuser can access all.
        """
        if not user_is_superuser_or_in_groups(self.request.user, ["Analyst"]):
            messages.error(self.request, msg_no_access)
            return redirect("dashboard:index")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.object = None
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        return self.render_to_response(self.get_context_data(form=form))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"create": True})
        if self.request.path == reverse("newdashboard:exposureupload-create"):
            self.template_name = "newdashboard/exposureupload_create.html"
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user, "dashboard_form": True})
        return kwargs

    def post(self, request, *args, **kwargs):
        self.object = None
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, self.success_message)
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        for error, message in form.errors.items():
            err = error.replace("_", " ").title()
            msg = message.as_text().replace("*", "")
            error_message = f"{err}: {msg}"
            messages.error(self.request, error_message)
        return self.render_to_response(self.get_context_data(form=form))


class ExposureUploadListView(LoginRequiredMixin, ListView):
    template_name = "dashboard/exposureupload_list.html"
    model = ExposureUpload

    def get_queryset(self):
        """
        Return user's ExposureUploads.
        Superuser can access all.
        """
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            qs = qs.filter(user=self.request.user)
        qs = qs.order_by("-id")
        return qs

    def dispatch(self, request, *args, **kwargs):
        """
        User must belong to the Analyst group.
        Superuser can access all.
        """
        if not user_is_superuser_or_in_groups(self.request.user, ["Analyst"]):
            messages.error(self.request, msg_no_access)
            return redirect("dashboard:index")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.path == reverse("newdashboard:exposureupload-list"):
            self.template_name = "newdashboard/exposureupload_list.html"
        return context


class ExposureUploadlDetailView(LoginRequiredMixin, DetailView):
    template_name = "dashboard/exposureupload_detail.html"
    model = ExposureUpload

    def dispatch(self, request, *args, **kwargs):
        """
        User must belong to the Analyst group.
        Superuser can access all.
        """
        instance = self.get_object()
        user_can_access = user_is_superuser_or_in_groups(self.request.user, ["Analyst"])
        # for non superuser, check if instance belongs to user
        if not self.request.user.is_superuser:
            if instance.user == self.request.user:
                user_can_access = True
            else:
                user_can_access = False
        if not user_can_access:
            messages.error(self.request, msg_no_access)
            return redirect("dashboard:index")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # instance = self.object
        if self.request.path == reverse(
            "newdashboard:exposureupload-detail", kwargs={"pk": self.object.id}
        ):
            self.template_name = "newdashboard/exposureupload_detail.html"
        return context


class ExposureUploadDeleteView(LoginRequiredMixin, DeleteView):
    template_name = "dashboard/exposureupload_delete.html"
    model = ExposureUpload
    success_url = reverse_lazy("newdashboard:exposureupload-list")
    success_message = _("Exposure upload successfully deleted.")

    def dispatch(self, request, *args, **kwargs):
        """
        User must belong to the Analyst group.
        Superuser can access all.
        """
        instance = self.get_object()
        user_can_access = user_is_superuser_or_in_groups(self.request.user, ["Analyst"])
        # for non superuser, check if instance belongs to user
        if not self.request.user.is_superuser:
            if instance.user == self.request.user:
                user_can_access = True
            else:
                user_can_access = False
        if not user_can_access:
            messages.error(self.request, msg_no_access)
            return redirect("dashboard:index")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        # use celery task since exposureupload deletion may be slow if there is
        # related exposure, exposurerecapitulation, and asset
        exposureupload_delete_task.delay(exposureupload_id=self.object.id)
        # self.object.delete()
        messages.success(self.request, self.success_message)
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.path == reverse(
            "newdashboard:exposureupload-delete", kwargs={"pk": self.object.id}
        ):
            self.template_name = "newdashboard/exposureupload_delete.html"
        return context


class OpenquakeJobCreateView(LoginRequiredMixin, CreateView):
    """
    Form page to create an OpenquakeJob
    """

    template_name = "dashboard/openquakejob_create.html"
    model = OpenquakeJob
    form_class = OpenquakeJobForm
    success_message = _("Risk Calculation job in progress, please wait...")

    def dispatch(self, request, *args, **kwargs):
        """
        User must belong to the Analyst group.
        Superuser can access all.

        Non-superuser cannot access outside job period if OPENQUAKE_JOB_PERIOD_ENABLE is true.
        """
        # check if OPENQUAKE_JOB_PERIOD_ENABLE is active for non superuser:
        if not self.request.user.is_superuser and constance_config.OPENQUAKE_JOB_PERIOD_ENABLE:
            now = datetime.now()
            if (
                now.time() < constance_config.OPENQUAKE_JOB_PERIOD_START
                or now.time() > constance_config.OPENQUAKE_JOB_PERIOD_END
            ):
                messages.error(self.request, msg_job_period)
                return redirect("dashboard:index")
        if not user_is_superuser_or_in_groups(self.request.user, ["Analyst"]):
            messages.error(self.request, msg_no_access)
            return redirect("dashboard:index")
        # check if calculation job quota reached
        if self.request.user.openquakejob_quota is not None:
            openquake_completed_jobs = OpenquakeJob.objects.filter(
                user=self.request.user, job_status="complete"
            ).count()
            if openquake_completed_jobs >= self.request.user.openquakejob_quota:
                messages.error(
                    self.request,
                    f"{msg_job_quota_reached}: {self.request.user.openquakejob_quota}",
                )
                return redirect("dashboard:openquakejob-list")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.object = None
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        return self.render_to_response(self.get_context_data(form=form))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"create": True})
        # check if openquake calculation servers are active
        # context.update({"calculation_server_active": airisiko_check_active_calculation_server("openquake")})
        context["calculation_server_active"] = airisiko_check_active_calculation_server(
            "openquake"
        )
        if self.request.path == reverse("newdashboard:openquakejob-create"):
            self.template_name = "newdashboard/openquakejob_create.html"
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user, "dashboard_form": True})
        return kwargs

    def post(self, request, *args, **kwargs):
        self.object = None
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, self.success_message)
        return redirect(
            reverse("dashboard:openquakejob-detail", kwargs={"pk": self.object.id})
        )

    def form_invalid(self, form):
        for error, message in form.errors.items():
            err = error.replace("_", " ").title()
            msg = message.as_text().replace("*", "")
            error_message = f"{err}: {msg}"
            messages.error(self.request, error_message)
        return self.render_to_response(self.get_context_data(form=form))


class OpenquakeJobListView(LoginRequiredMixin, ListView):
    """
    Listing page for OpenquakeJobs.
    """

    template_name = "dashboard/openquakejob_list.html"
    model = OpenquakeJob

    def get_queryset(self):
        """
        Return user's OpenquakeJobs.
        Superuser can access all.
        """
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            qs = qs.filter(user=self.request.user)
        qs = qs.order_by("-id")
        return qs

    def dispatch(self, request, *args, **kwargs):
        """
        User must belong to the Analyst group.
        Superuser can access all.
        """
        if not user_is_superuser_or_in_groups(self.request.user, ["Analyst"]):
            messages.error(self.request, msg_no_access)
            return redirect("dashboard:index")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        openquake_completed_jobs = OpenquakeJob.objects.filter(
            user=self.request.user, job_status="complete"
        ).count()
        context.update({"openquake_completed_jobs": openquake_completed_jobs})
        if self.request.path == reverse("newdashboard:openquakejob-list"):
            self.template_name = "newdashboard/openquakejob_list.html"
        return context


class OpenquakeJobDetailView(LoginRequiredMixin, DetailView):
    """
    Detail page about an OpenquakeJob.
    """

    template_name = "dashboard/openquakejob_detail.html"
    model = OpenquakeJob

    def dispatch(self, request, *args, **kwargs):
        """
        User must belong to the Analyst group.
        Superuser can access all.
        """
        instance = self.get_object()
        user_can_access = user_is_superuser_or_in_groups(self.request.user, ["Analyst"])
        # for non superuser, check if instance belongs to user
        if not self.request.user.is_superuser:
            if instance.user == self.request.user:
                user_can_access = True
            else:
                user_can_access = False
        if not user_can_access:
            messages.error(self.request, msg_no_access)
            return redirect("dashboard:index")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # instance = self.object
        if self.request.path == reverse(
            "newdashboard:openquakejob-detail", kwargs={"pk": self.object.id}
        ):
            self.template_name = "newdashboard/openquakejob_detail.html"
        return context


class OpenquakeJobAbortView(LoginRequiredMixin, DeleteView):
    """
    Abort a job from the OpenQuake server with confirmation page.
    """

    template_name = "dashboard/openquakejob_abort.html"
    model = OpenquakeJob
    success_url = reverse_lazy("newdashboard:openquakejob-list")

    def dispatch(self, request, *args, **kwargs):
        """
        User must belong to the Analyst group.
        Superuser can access all.

        Job status must be created or executing.
        """
        instance = self.get_object()
        user_can_access = user_is_superuser_or_in_groups(self.request.user, ["Analyst"])
        # for non superuser, check if instance belongs to user
        if not self.request.user.is_superuser:
            if instance.user == self.request.user:
                user_can_access = True
            else:
                user_can_access = False
        if instance.job_status == "created" or instance.job_status == "executing":
            user_can_access = True
        else:
            messages.error(self.request, msg_job_cannot_abort)
            return redirect(self.get_success_url())
        if not user_can_access:
            messages.error(self.request, msg_no_access)
            return redirect("dashboard:index")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.job_status == "created" or self.object.job_status == "executing":
            openquake_abort_calc_task.delay(openquakejob_id=self.object.id)
            messages.success(self.request, msg_job_stopped)
        else:
            messages.error(self.request, msg_job_stop_failed)
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.path == reverse(
            "newdashboard:openquakejob-abort", kwargs={"pk": self.object.id}
        ):
            self.template_name = "newdashboard/openquakejob_abort.html"
        return context


class OpenquakeJobRemoveView(LoginRequiredMixin, DeleteView):
    """
    Remove a job from the OpenQuake server with confirmation page.
    """

    template_name = "dashboard/openquakejob_remove.html"
    model = OpenquakeJob
    success_url = reverse_lazy("newdashboard:openquakejob-list")

    def dispatch(self, request, *args, **kwargs):
        """
        Only superuser can access.

        Job status must be complete, aborted, or failed.
        """
        instance = self.get_object()
        user_can_access = False
        if self.request.user.is_superuser:
            user_can_access = True
        if (
            instance.job_status == "complete"
            or instance.job_status == "aborted"
            or instance.job_status == "failed"
        ):
            user_can_access = True
        else:
            messages.error(self.request, msg_job_cannot_remove)
            return redirect(self.get_success_url())
        if not user_can_access:
            messages.error(self.request, msg_no_access)
            return redirect("dashboard:index")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if (
            self.object.job_status == "complete"
            or self.object.job_status == "aborted"
            or self.object.job_status == "failed"
        ):
            openquake_remove_calc_task.delay(openquakejob_id=self.object.id)
            messages.success(self.request, msg_job_removed)
        else:
            messages.error(self.request, msg_job_remove_failed)
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.path == reverse(
            "newdashboard:openquakejob-remove", kwargs={"pk": self.object.id}
        ):
            self.template_name = "newdashboard/openquakejob_remove.html"
        return context


class OpenquakeJobDeleteView(LoginRequiredMixin, DeleteView):
    """
    Delete an OpenquakeJob record with confirmation page.
    """

    template_name = "dashboard/openquakejob_delete.html"
    model = OpenquakeJob
    success_url = reverse_lazy("newdashboard:openquakejob-list")
    success_message = _("Risk Calculation job successfully deleted.")

    def dispatch(self, request, *args, **kwargs):
        """
        User must belong to the Analyst group.
        Superuser can access all.
        """
        instance = self.get_object()
        user_can_access = user_is_superuser_or_in_groups(self.request.user, ["Analyst"])
        # for non superuser, check if instance belongs to user
        if not self.request.user.is_superuser:
            if instance.user == self.request.user:
                user_can_access = True
                # non superuser cannot delete completed job to reduce quota usage!
                if instance.job_status == "complete":
                    messages.error(self.request, msg_job_cannot_delete_completed)
                    return redirect(self.get_success_url())
            else:
                user_can_access = False
        if not user_can_access:
            messages.error(self.request, msg_no_access)
            return redirect("dashboard:index")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        # if job status is running try to abort first
        if self.object.job_status == "created" or self.object.job_status == "executing":
            openquake_abort_calc_task.delay(openquakejob_id=self.object.id, delete=True)
            messages.success(self.request, msg_job_stopped)
        else:
            self.object.delete()
        messages.success(self.request, self.success_message)
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.path == reverse(
            "newdashboard:openquakejob-delete", kwargs={"pk": self.object.id}
        ):
            self.template_name = "newdashboard/openquakejob_delete.html"
        return context


class HazardListView(LoginRequiredMixin, TemplateView):
    """
    TODO Placeholder page for Hazard.
    """

    template_name = "dashboard/hazard_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.path == reverse("newdashboard:hazard-list"):
            self.template_name = "newdashboard/hazard_list.html"
        return context


class EventListView(LoginRequiredMixin, TemplateView):
    """
    TODO Placeholder page for Event.
    """

    template_name = "dashboard/event_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.path == reverse("newdashboard:event-list"):
            self.template_name = "newdashboard/event_list.html"
        return context


class VulnerabilityListView(LoginRequiredMixin, TemplateView):
    """
    TODO Placeholder page for Vulnerability.
    """

    template_name = "dashboard/vulnerability_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.path == reverse("newdashboard:vulnerability-list"):
            self.template_name = "newdashboard/vulnerability_list.html"
        return context


class RiskMatrixListView(LoginRequiredMixin, ListView):
    """
    Listing page for Risk Matrixes from OpenquakeJobs.
    """

    template_name = "dashboard/risk_matrix_list.html"
    model = OpenquakeJob

    def get_queryset(self):
        """
        Return user's OpenquakeJobs.
        Superuser can access all.
        """
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            qs = qs.filter(user=self.request.user)
        qs = qs.order_by("-id")
        return qs

    def dispatch(self, request, *args, **kwargs):
        """
        User must belong to the Analyst group.
        Superuser can access all.
        """
        if not user_is_superuser_or_in_groups(self.request.user, ["Analyst"]):
            messages.error(self.request, msg_no_access)
            return redirect("dashboard:index")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.path == reverse("newdashboard:risk-matrix-list"):
            self.template_name = "newdashboard/risk_matrix_list.html"
        return context


class RiskMatrixDetailView(LoginRequiredMixin, TemplateView):
    """
    Risk Matrix for displaying an OpenquakeJob's related OpenquakeAAL, and OpenquakePML details.
    """

    template_name = "dashboard/risk_matrix_detail.html"

    def dispatch(self, request, *args, **kwargs):
        """
        User must belong to the Analyst group.
        Superuser can access all.
        """
        openquakejob_id = kwargs.get("openquakejob_id")
        instance = get_object_or_404(OpenquakeJob, pk=openquakejob_id)
        user_can_access = user_is_superuser_or_in_groups(self.request.user, ["Analyst"])
        # for non superuser, check if instance belongs to user
        if not self.request.user.is_superuser:
            if instance.user == self.request.user:
                user_can_access = True
            else:
                user_can_access = False
        if not user_can_access:
            messages.error(self.request, msg_no_access)
            return redirect("dashboard:index")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        openquakejob_id = kwargs.get("openquakejob_id")
        openquakejob = get_object_or_404(OpenquakeJob, pk=openquakejob_id)
        aal_national = OpenquakeAAL.objects.filter(
            openquakejob=openquakejob, province="", city=""
        )
        pmls = OpenquakePML.objects.filter(openquakejob=openquakejob).order_by(
            "return_period"
        )
        pml_eps = OpenquakePML.objects.filter(openquakejob=openquakejob).order_by(
            "-return_period"
        )
        pml200 = pmls.filter(return_period=200)
        if openquakejob.exposure:
            exposure_recap = openquakejob.exposure.exposurerecapitulations.all()
            if exposure_recap:
                context["total_exposure"] = exposure_recap.filter(
                    province="", city=""
                ).first()
            # set defaults, if exposure is created from api then exposure_upload is null!
            context["currency_code"] = (
                openquakejob.exposure.exposure_upload.currency_code
                if openquakejob.exposure.exposure_upload
                else "IDR"
            )
            context["decimal_separator"] = (
                openquakejob.exposure.exposure_upload.decimal_separator
                if openquakejob.exposure.exposure_upload
                else ","
            )
        context["openquakejob"] = openquakejob
        context["aal_national"] = aal_national.first()
        context["pmls"] = pmls
        context["pml_eps"] = pml_eps
        context["pml200"] = pml200.first()
        aal_cities = (
            OpenquakeAAL.objects.filter(
                ~Q(province=""), ~Q(city=""), openquakejob=openquakejob
            )
            .defer("provinsi__polygon", "kabupaten_kota__polygon")
            .order_by("-loss_ratio")
        )  # defer large polygon
        if aal_cities:
            context["aal_highest_city"] = aal_cities.first()
        aal_provinces = (
            OpenquakeAAL.objects.filter(
                ~Q(province=""), openquakejob=openquakejob, city=""
            )
            .defer("provinsi__polygon", "kabupaten_kota__polygon")
            .order_by("-loss_ratio")
        )
        if aal_provinces:
            context["aal_highest_province"] = aal_provinces.first()
        city = self.request.GET.get("city", None)
        if city:
            context["aals"] = aal_cities
        else:
            context["aals"] = aal_provinces
        elt_file = openquakejob.result_files.all().filter(
            name="Aggregated Risk By Event (.csv)"
        )
        if elt_file:
            context["elt_file"] = elt_file[0]
        if self.request.path == reverse(
            "newdashboard:risk-matrix-detail",
            kwargs={"openquakejob_id": openquakejob_id},
        ):
            self.template_name = "newdashboard/risk_matrix_detail.html"
        return context


class ExposureRecapitulationView(LoginRequiredMixin, TemplateView):
    """
    Exposure Recapitulation.
    """

    template_name = "dashboard/exposure_recapitulation.html"

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        exposureupload_id = kwargs.get("exposureupload_id")
        exposureupload = get_object_or_404(ExposureUpload, pk=exposureupload_id)
        exposure = exposureupload.exposures.all().first()
        exposure_recapitulation = ExposureRecapitulation.objects.filter(
            exposure=exposure
        )
        exposure_national = exposure_recapitulation.filter(province="", city="").first()
        exposure_provinces = exposure_recapitulation.filter(
            ~Q(province=""), city=""
        ).order_by("-total")
        exposure_cities = exposure_recapitulation.filter(
            ~Q(province=""), ~Q(city="")
        ).order_by("-total")
        context["exposureupload"] = exposureupload
        context["currency_code"] = exposureupload.currency_code
        context["exposure_national"] = exposure_national
        context["exposure_provinces"] = exposure_provinces
        context["exposure_cities"] = exposure_cities
        if self.request.path == reverse(
            "newdashboard:exposure-recapitulation",
            kwargs={"exposureupload_id": exposureupload_id},
        ):
            self.template_name = "newdashboard/exposure_recapitulation.html"
        return context


class DocumentsView(LoginRequiredMixin, TemplateView):
    """
    Static documents list page.
    """

    template_name = "dashboard/documents.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.path == reverse("newdashboard:documents"):
            self.template_name = "newdashboard/documents.html"
        return context


class VulnerabilityInformationListView(LoginRequiredMixin, ListView):
    """
    Listing page for VulnerabilityInformation.
    """

    template_name = "dashboard/vulnerabilityinformation_list.html"
    model = VulnerabilityInformation

    def dispatch(self, request, *args, **kwargs):
        """
        User must belong to the Analyst group.
        Superuser can access all.
        """
        if not user_is_superuser_or_in_groups(self.request.user, ["Analyst"]):
            messages.error(self.request, msg_no_access)
            return redirect("dashboard:index")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class VulnerabilityInformationDetailView(LoginRequiredMixin, DetailView):
    """
    Detail page about an OpenquakeJob.
    """

    template_name = "dashboard/vulnerabilityinformation_detail.html"
    model = VulnerabilityInformation

    def dispatch(self, request, *args, **kwargs):
        """
        User must belong to the Analyst group.
        Superuser can access all.
        """
        user_can_access = user_is_superuser_or_in_groups(self.request.user, ["Analyst"])
        if not user_can_access:
            messages.error(self.request, msg_no_access)
            return redirect("dashboard:index")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        instance = self.object
        if instance.file_path:
            general_information = {}
            if instance.file_path.lower().startswith(
                "http"
            ) or instance.file_path.lower().startswith("https"):
                pass
            else:
                try:
                    json_file_path = os.path.join(
                        settings.MEDIA_ROOT, instance.file_path
                    )
                    if os.path.isfile(json_file_path):
                        with open(json_file_path) as json_file:
                            vi_details = json.load(json_file)
                            if "fields" in vi_details:
                                general_information["name"] = vi_details["fields"][
                                    "name"
                                ]
                                general_information["category"] = vi_details["fields"][
                                    "category"
                                ]
                                general_information["taxonomy_text"] = vi_details[
                                    "fields"
                                ]["taxonomy_text"]
                                general_information["type_of_assessment"] = vi_details[
                                    "fields"
                                ]["type_of_assessment"]
                                general_information[
                                    "reference"
                                ] = f'{vi_details["fields"]["article_title"]} ({vi_details["fields"]["authors"]}, {vi_details["fields"]["year"]}) - {vi_details["fields"]["publication_conference_name"]}'  # noqa
                                general_information["web_link"] = vi_details["fields"][
                                    "web_link"
                                ]
                                general_information[
                                    "method_of_estimation"
                                ] = vi_details["fields"]["fragility_func"]["fields"][
                                    "method_of_estimation"
                                ]
                                general_information["general_comments"] = vi_details[
                                    "fields"
                                ]["general_comments"]
                except Exception as err:
                    logging.error(f"ERROR: {err}")
            context.update({"general_information": general_information})
        return context


@login_required
def test_create_openquakejob_from_exposure(request):
    """
    /dashboard/oq/test1/
    """
    if request.method == "POST" and request.user.is_superuser:
        a = request.POST.get("a")
        print(a)
        mem_zip = io.BytesIO()
        # zipi = zipfile.ZipInfo()
        file_paths = [
            "job.ini",
            "EXPOSURE/ATMAJA_22_ID_RES_COMP/exposure_model.xml",
            "EXPOSURE/ATMAJA_22_ID_RES_COMP/Exposure_Res_All_Indonesia.csv",
            "HAZARD/PUSGEN_17_IDN/ssmLT.xml",
            "HAZARD/PUSGEN_17_IDN/gmmLT_PetaGempa2017.xml",
            "HAZARD/PUSGEN_17_IDN/crustalfault/Indonesia_Crustal_faults.xml",
            "HAZARD/PUSGEN_17_IDN/deepgrid/deepgrid_layer1_50_100.xml",
            "HAZARD/PUSGEN_17_IDN/deepgrid/deepgrid_layer2_100_150.xml",
            "HAZARD/PUSGEN_17_IDN/deepgrid/deepgrid_layer3_150_200.xml",
            "HAZARD/PUSGEN_17_IDN/deepgrid/deepgrid_layer4_200_300.xml",
            "HAZARD/PUSGEN_17_IDN/shallowgrid/shallowgrid_layer1_0_25.xml",
            "HAZARD/PUSGEN_17_IDN/shallowgrid/shallowgrid_layer2_25_50.xml",
            "HAZARD/PUSGEN_17_IDN/sub/Indonesia_Sub.xml",
            "HAZARD/USGS_20_GLOBAL_VS30/Vs30_All_Indonesia.csv",
            "VULNERABILITY/GORO_21_ID/vulnerability_total_Indonesia.xml",
        ]
        files_to_zip = []
        for file_path in file_paths:
            zipi = zipfile.ZipInfo()
            zipi.filename = file_path
            zipi.compress_type = zipfile.ZIP_DEFLATED
            files_to_zip.append(
                (
                    zipi,
                    os.path.join(
                        settings.STATICFILES_DIRS[0],
                        "openquakejobtemplate",
                        "v1",
                        file_path,
                    ),
                ),
            )
        COMPRESSION_LEVEL = 5
        with zipfile.ZipFile(
            mem_zip,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=COMPRESSION_LEVEL,
        ) as zf:
            for f in files_to_zip:
                with open(f[1]) as fh:
                    zf.writestr(f[0], fh.read())
        full_zip_in_memory = mem_zip.getvalue()
        form = OpenquakeJobForm()
        openquakejob = form.save(commit=False)
        openquakejob.name = "test create openquake job from created zip"
        openquakejob.user = request.user
        openquakejob.file = files.File(ContentFile(full_zip_in_memory, "job.zip"))
        openquakejob.save()
        res = openquake_submit_calc_task.delay(openquakejob_id=openquakejob.id)
        openquakejob.task_id = res.id
        openquakejob.task_state = res.state
        openquakejob.save()
        response = HttpResponse(
            full_zip_in_memory, content_type="application/force-download"
        )
        response["Content-Disposition"] = "attachment; filename={}".format("job.zip")
        return response
    return render(request, "dashboard/test_create_openquakejob_from_exposure.html", {})
