import logging
from datetime import datetime

from constance import config as constance_config
from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, authentication_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from ai_risiko.airisiko.models import (
    Asset,
    CalculationServer,
    Exposure,
    Kabupaten_Kota,
    OpenquakeAAL,
    OpenquakeJob,
)
from ai_risiko.airisiko.tasks import (
    exposure_recapitulate_task,
    openquake_abort_calc_task,
    openquake_remove_calc_task,
    openquake_submit_calc_task,
)
from ai_risiko.dashboard.views import user_is_superuser_or_in_groups
from ai_risiko.users.api.serializers import UserSerializer


def is_ajax(request):
    return request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"


@login_required
def oq_job_details(request):
    """
    Return the task and job details of an OpenquakeJob.
    """
    if is_ajax(request):
        try:
            openquakejob_id = request.GET.get("id")
            if request.user.is_superuser:
                openquakejob = get_object_or_404(OpenquakeJob, pk=openquakejob_id)
            else:
                openquakejob = get_object_or_404(
                    OpenquakeJob,
                    pk=openquakejob_id,
                    user=request.user,
                )
            data = {
                "info": openquakejob.info,
                "task_state": openquakejob.task_state,
                "job_id": openquakejob.job_id,
                "job_status": openquakejob.job_status,
                "job_message": openquakejob.job_message,
            }
            return JsonResponse({"success": True, "data": data})
        except Exception as e:
            return JsonResponse({"success": False, "error": e})


def get_asset_dict(asset):
    asset_longitude = ""
    asset_latitude = ""
    if asset["point"]:
        asset_longitude = asset["point"][0]
        asset_latitude = asset["point"][1]
    asset_dict = {
        "id": asset["id"],
        "lon": asset_longitude,
        "lat": asset_latitude,
        "taxonomy": asset["taxonomy"],
        "number": asset["asset_id"],
        "structural": asset["structural"],
        "night": asset["night"],
        "material": asset["material"],
        "llrs": asset["llrs"],
        "code": asset["code"],
        "height": asset["height"],
        "occupancy": asset["occupancy"],
        "name": asset["name"],
        "name_1": asset["province"],
        "name_2": asset["city"],
        "id_1": asset["city_code"],
        "kabupaten_kota_id": asset["kabupaten_kota_id"],
    }
    return asset_dict


@api_view(["GET"])
@authentication_classes([TokenAuthentication])
def exposure(request, exposure_id=None):
    """
    Return array of Exposures or single Exposure details.

    Superuser can get any Exposure, others can only get owned Exposure.
    """
    if exposure_id:  # return exposure dict
        exposure = None
        if request.user.is_superuser:
            exposure = get_object_or_404(Exposure, pk=exposure_id)
        else:
            exposure = get_object_or_404(Exposure, pk=exposure_id, user=request.user)
        exposure_assets = []
        for (
            asset
        ) in (
            exposure.assets.all().values()
        ):  # use values() to exclude kabupaten_kota polygon fields
            asset_dict = get_asset_dict(asset)
            exposure_assets.append(asset_dict)
        user_serialized = UserSerializer(exposure.user, context={"request": request})
        exposure_data = {
            "id": exposure.id,
            "created": exposure.created,
            "updated": exposure.updated,
            "user": user_serialized.data,
            "assets": exposure_assets,
        }
        response = JsonResponse(exposure_data)
    else:  # return array of exposure dicts
        exposures = None
        if request.user.is_superuser:
            exposures = Exposure.objects.all()
        else:
            exposures = Exposure.objects.filter(user=request.user)
        exposures_data = []
        for exposure in exposures:
            exposure_assets = []
            for asset in exposure.assets.all().values():
                asset_dict = get_asset_dict(asset)
                exposure_assets.append(asset_dict)
            user_serialized = UserSerializer(
                exposure.user, context={"request": request}
            )
            exposure_data = {
                "id": exposure.id,
                "created": exposure.created,
                "updated": exposure.updated,
                "user": user_serialized.data,
                "assets": exposure_assets,
            }
            exposures_data.append(exposure_data)
        response = JsonResponse(exposures_data, safe=False)
    return response


@api_view(["GET"])
@authentication_classes([TokenAuthentication])
def exposure_recapitulation(request, exposure_id):
    """
    Return array of ExposureRecapitulations of an Exposure.

    Superuser can get any Exposure, others can only get owned Exposure.
    """
    if exposure_id:
        exposure = None
        if request.user.is_superuser:
            exposure = get_object_or_404(Exposure, pk=exposure_id)
        else:
            exposure = get_object_or_404(Exposure, pk=exposure_id, user=request.user)
        exposure_recap_data = []
        for exposure_recap in exposure.exposurerecapitulations.all():
            exposure_recap_dict = {
                "province": exposure_recap.province,
                "city": exposure_recap.city,
                "total": exposure_recap.total,
            }
            exposure_recap_data.append(exposure_recap_dict)
        response = JsonResponse(exposure_recap_data, safe=False)
    else:
        response = Response(
            status=status.HTTP_400_BAD_REQUEST,
            data={"success": False, "message": "Missing 'exposure_id' parameter."},
        )
    return response


# @api_view(["POST"])
# @authentication_classes([TokenAuthentication])
def exposure_create(request):
    """
    Create a new Exposure. Similar to save_exposure_csv() implementation.
    """
    # user must be Superuser or Analyst
    if not user_is_superuser_or_in_groups(request.user, ["Analyst"]):
        response = Response(
            status=status.HTTP_403_FORBIDDEN,
            data={"success": False, "message": "Access forbidden."},
        )
        return response
    if request.data:
        csv_ids = [str(asset_obj.get("id", "")) for asset_obj in request.data]
        non_empty_csv_ids = [c for c in csv_ids if c]
        if len(non_empty_csv_ids) != len(set(non_empty_csv_ids)):
            response = Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={
                    "success": False,
                    "message": "Duplicate csv_id ('id') found in the batch; csv_id must be unique.",
                },
            )
            return response
        with transaction.atomic():
            exposure = Exposure()
            # exposure.name = instance.name
            exposure.save()
            asset_count = 0
            for asset_obj in request.data:
                asset = Asset()
                asset.name = asset_obj.get("name", "")
                asset.address = asset_obj.get("address", "")
                asset.type = asset_obj.get("type", "")
                asset_latitude = asset_obj.get("lat", "")
                asset_longitude = asset_obj.get("lon", "")
                if asset_latitude and asset_longitude:
                    try:
                        asset.point = Point(
                            float(asset_longitude), float(asset_latitude)
                        )
                        kabupaten_kota = Kabupaten_Kota.objects.filter(
                            polygon__contains=asset.point
                        ).order_by("id")
                        if kabupaten_kota:
                            asset.kabupaten_kota = kabupaten_kota[0]
                    except ValueError:
                        pass
                asset.occupancy = asset_obj.get("occupancy", "")
                asset.csv_id = asset_obj.get("id", "")
                asset.asset_id = asset_obj.get("number", "")
                asset.taxonomy = asset_obj.get("taxonomy", "")
                asset.structural = asset_obj.get("structural", "")
                asset.occupancy_description = asset_obj.get("occupancy_desc", "")
                asset.province = asset_obj.get("name_1", "")
                asset.city = asset_obj.get("name_2", "")
                asset.city_code = asset_obj.get("id_1", "")
                asset.material = asset_obj.get("material", "")
                asset.llrs = asset_obj.get("llrs", "")
                asset.code = asset_obj.get("code", "")
                asset.ductility = asset_obj.get("ductility", "")
                asset.height = asset_obj.get("height", "")
                asset.night = asset_obj.get("night", "")
                asset.group = asset_obj.get("group", "")
                try:
                    # validate instance first
                    asset.full_clean()
                    asset.save()
                    # add asset to exposure m2m relationship
                    exposure.assets.add(asset)
                    asset_count += 1
                except ValidationError as e:
                    for k, v in e.message_dict.items():
                        error_msg = f'- WARNING obj {asset_count}: save error for Asset field "{k}" => {v}'
                        logging.warning(error_msg)
                except Exception as err:
                    logging.error(f"ERROR exposure_create: {err}")
            exposure.name = f"api_exposure_{exposure.id}-{request.user.username}"
            exposure.user = request.user
            exposure.save()
            # call synchronously since operation is atomic
            exposure_recapitulate_task.s(exposure_id=exposure.id).apply()
            response = Response(
                status=status.HTTP_201_CREATED,
                data={"success": True, "exposure_id": exposure.id},
            )
    else:
        response = Response(
            status=status.HTTP_400_BAD_REQUEST,
            data={"success": False, "message": "Missing assets data."},
        )
    return response


class ExposureCreateView(APIView):
    """
    API view to create a new Exposure with assets.

    Reimplement exposure_create() as class-based view for throttling support.
    """

    authentication_classes = [TokenAuthentication]
    throttle_scope = "exposure_create"

    def post(self, request, format=None):
        return exposure_create(request)


# @api_view(["DELETE"])
# @authentication_classes([TokenAuthentication])
def exposure_delete(request):
    """
    Delete single owned Exposure, ExposureRecapitulations, and related Assets.

    Superuser can delete any Exposure, others can only delete owned Exposure.
    """
    exposure_id = request.data.get("exposure_id")
    if exposure_id:
        exposure = None
        if request.user.is_superuser:
            exposure = get_object_or_404(Exposure, pk=exposure_id)
        else:
            exposure = get_object_or_404(Exposure, pk=exposure_id, user=request.user)
        exposure.assets.all().delete()
        exposure.delete()  # also deletes ExposureRecapitulations
        response = Response(
            status=status.HTTP_200_OK,
            data={
                "success": True,
                "message": "Exposure, Exposure Recapitulations, and Assets successfully deleted.",
            },
        )
    else:
        response = Response(
            status=status.HTTP_400_BAD_REQUEST,
            data={"success": False, "message": "Missing 'exposure_id' parameter."},
        )
    return response


class ExposureDeleteView(APIView):
    """
    API view to delete a single owned Exposure, ExposureRecapitulations, and related Assets.

    Reimplement exposure_delete() as class-based view for throttling support.
    """

    authentication_classes = [TokenAuthentication]
    throttle_scope = "exposure_delete"

    def delete(self, request, format=None):
        return exposure_delete(request)


def get_openquakejob_dict(openquakejob):
    file_url = openquakejob.file.url if openquakejob.file else None
    job_results_datastore_file_url = (
        openquakejob.job_results_datastore_file.url
        if openquakejob.job_results_datastore_file
        else None
    )
    calculationserver_id = (
        openquakejob.calculation_server.id if openquakejob.calculation_server else None
    )
    exposure_id = openquakejob.exposure.id if openquakejob.exposure else None
    result_files = []
    for result_file in openquakejob.result_files.all():
        result_file_dict = {"name": result_file.name, "url": result_file.file.url}
        result_files.append(result_file_dict)
    openquakejob_dict = {
        "id": openquakejob.id,
        "created": openquakejob.created,
        "updated": openquakejob.updated,
        "name": openquakejob.name,
        "calculationserver_id": calculationserver_id,
        "exposure_id": exposure_id,
        "file": file_url,
        "info": openquakejob.info,
        "task_id": openquakejob.task_id,
        "task_state": openquakejob.task_state,
        "task_start": openquakejob.task_start,
        "task_end": openquakejob.task_end,
        "job_id": openquakejob.job_id,
        "job_status": openquakejob.job_status,
        "job_message": openquakejob.job_message,
        "job_results": openquakejob.job_results,
        "job_results_datastore_file": job_results_datastore_file_url,
        "result_files": result_files,
    }
    return openquakejob_dict


@api_view(["GET"])
@authentication_classes([TokenAuthentication])
def eq(request, openquakejob_id=None):
    """
    Return array of OpenquakeJobs or single OpenquakeJob details.

    Superuser can get any OpenquakeJob, others can only get owned OpenquakeJob.
    """
    if openquakejob_id:  # return openquakejob dict
        openquakejob = None
        if request.user.is_superuser:
            openquakejob = get_object_or_404(OpenquakeJob, pk=openquakejob_id)
        else:
            openquakejob = get_object_or_404(
                OpenquakeJob, pk=openquakejob_id, user=request.user
            )
        user_serialized = UserSerializer(
            openquakejob.user, context={"request": request}
        )
        openquakejob_dict = get_openquakejob_dict(openquakejob)
        openquakejob_dict["user"] = user_serialized.data
        response = JsonResponse(openquakejob_dict)
    else:  # return array of openquakejob dicts
        openquakejobs = None
        if request.user.is_superuser:
            openquakejobs = OpenquakeJob.objects.all()
        else:
            openquakejobs = OpenquakeJob.objects.filter(user=request.user)
        openquakejob_data = []
        for openquakejob in openquakejobs:
            user_serialized = UserSerializer(
                openquakejob.user, context={"request": request}
            )
            openquakejob_dict = get_openquakejob_dict(openquakejob)
            openquakejob_data.append(openquakejob_dict)
        response = JsonResponse(openquakejob_data, safe=False)
    return response


# @api_view(["POST"])
# @authentication_classes([TokenAuthentication])
def eq_create(request):
    """
    Create an OpenQuake job. Similar to OpenquakeJobCreateView and OpenquakeJobForm implementation.
    """
    if request.data:
        name = request.data.get("name")
        exposure_id = request.data.get("exposure_id")
        if not name or not exposure_id:
            response = Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={
                    "success": False,
                    "message": "Missing 'name' or 'exposure_id' parameter.",
                },
            )
        exposure = None
        if request.user.is_superuser:
            exposure = get_object_or_404(Exposure, pk=exposure_id)
        else:
            exposure = get_object_or_404(Exposure, pk=exposure_id, user=request.user)
        # check risk calculation open time period
        if not request.user.is_superuser and constance_config.OPENQUAKE_JOB_PERIOD_ENABLE:
            now = datetime.now()
            if (
                now.time() < constance_config.OPENQUAKE_JOB_PERIOD_START
                or now.time() > constance_config.OPENQUAKE_JOB_PERIOD_END
            ):
                response = Response(
                    status=status.HTTP_403_FORBIDDEN,
                    data={
                        "success": False,
                        "message": (
                            f"Risk Calculation job is only available from {constance_config.OPENQUAKE_JOB_PERIOD_START}"
                            f" - {constance_config.OPENQUAKE_JOB_PERIOD_END}."
                        ),
                    },
                )
                return response
        # user must be Superuser or Analyst
        if not user_is_superuser_or_in_groups(request.user, ["Analyst"]):
            response = Response(
                status=status.HTTP_403_FORBIDDEN,
                data={"success": False, "message": "Access forbidden."},
            )
            return response
        # check if calculation job quota reached
        if request.user.openquakejob_quota is not None:
            openquake_completed_jobs = OpenquakeJob.objects.filter(
                user=request.user, job_status="complete"
            ).count()
            if openquake_completed_jobs >= request.user.openquakejob_quota:
                response = Response(
                    status=status.HTTP_403_FORBIDDEN,
                    data={
                        "success": False,
                        "message": "Cannot create new Risk Calculation job. You have reached your quota.",
                    },
                )
                return response
        # create new OpenquakeJob
        openquakejob = OpenquakeJob()
        openquakejob.name = name
        openquakejob.exposure = exposure
        openquakejob.user = request.user
        try:
            # validate instance first
            openquakejob.full_clean()
            openquakejob.save()
        except ValidationError as e:
            for k, v in e.message_dict.items():
                error_msg = f'- ERROR: save error for OpenquakeJob field "{k}" => {v}'
                logging.warning(error_msg)
                response = Response(
                    status=status.HTTP_400_BAD_REQUEST,
                    data={"success": False, "message": error_msg},
                )
                return response
        response = Response(
            status=status.HTTP_201_CREATED,
            data={"success": True, "openquakejob_id": openquakejob.id},
        )
    else:
        response = Response(
            status=status.HTTP_400_BAD_REQUEST,
            data={
                "success": False,
                "message": "Missing 'name' and 'exposure_id' parameter.",
            },
        )
    return response


class EqCreateView(APIView):
    """
    API view to create an OpenQuake job.

    Reimplement eq_create() as class-based view for throttling support.
    """

    authentication_classes = [TokenAuthentication]
    throttle_scope = "eq_create"

    def post(self, request, format=None):
        return eq_create(request)


# @api_view(["POST"])
# @authentication_classes([TokenAuthentication])
def eq_start(request):
    """
    Start an OpenQuake job. Similar to OpenquakeJobCreateView and OpenquakeJobForm implementation.

    Superuser can start any OpenquakeJob, others can only start owned OpenquakeJob.
    """
    openquakejob_id = request.data.get("openquakejob_id")
    if openquakejob_id:
        openquakejob = None
        if request.user.is_superuser:
            openquakejob = get_object_or_404(OpenquakeJob, pk=openquakejob_id)
        else:
            openquakejob = get_object_or_404(
                OpenquakeJob, pk=openquakejob_id, user=request.user
            )
        # check risk calculation open time period
        if not request.user.is_superuser and constance_config.OPENQUAKE_JOB_PERIOD_ENABLE:
            now = datetime.now()
            if (
                now.time() < constance_config.OPENQUAKE_JOB_PERIOD_START
                or now.time() > constance_config.OPENQUAKE_JOB_PERIOD_END
            ):
                response = Response(
                    status=status.HTTP_403_FORBIDDEN,
                    data={
                        "success": False,
                        "message": (
                            f"Risk Calculation job is only available from {constance_config.OPENQUAKE_JOB_PERIOD_START}"
                            f" - {constance_config.OPENQUAKE_JOB_PERIOD_END}."
                        ),
                    },
                )
                return response
        # user must be Superuser or Analyst
        if not user_is_superuser_or_in_groups(request.user, ["Analyst"]):
            response = Response(
                status=status.HTTP_403_FORBIDDEN,
                data={"success": False, "message": "Access forbidden."},
            )
            return response
        res = openquake_submit_calc_task.delay(openquakejob_id=openquakejob.id)
        openquakejob.task_id = res.id
        openquakejob.task_state = res.state
        openquakejob.save()
        response = Response(
            status=status.HTTP_200_OK,
            data={
                "success": True,
                "message": "Risk Calculation job has been submitted to the Calculation Server to start.",
            },
        )
    else:
        response = Response(
            status=status.HTTP_400_BAD_REQUEST,
            data={"success": False, "message": "Missing 'openquakejob_id' parameter."},
        )
    return response


class EqStartView(APIView):
    """
    API view to start an OpenQuake job.

    Reimplement eq_start() as class-based view for throttling support.
    """

    authentication_classes = [TokenAuthentication]
    throttle_scope = "eq_start"

    def post(self, request, format=None):
        return eq_start(request)


# @api_view(["POST"])
# @authentication_classes([TokenAuthentication])
def eq_abort(request):
    """
    Abort create/executing OpenQuake job. Similar to OpenquakeJobAbortView implementation.

    Superuser can abort any OpenquakeJob, others can only abort owned OpenquakeJob.

    Job status must be 'created' or 'executing'.
    """
    openquakejob_id = request.data.get("openquakejob_id")
    if openquakejob_id:
        openquakejob = None
        if request.user.is_superuser:
            openquakejob = get_object_or_404(OpenquakeJob, pk=openquakejob_id)
        else:
            openquakejob = get_object_or_404(
                OpenquakeJob, pk=openquakejob_id, user=request.user
            )
        if (
            openquakejob.job_status == "created"
            or openquakejob.job_status == "executing"
        ):
            openquake_abort_calc_task.delay(openquakejob_id=openquakejob.id)
            response = Response(
                status=status.HTTP_200_OK,
                data={
                    "success": True,
                    "message": "Risk Calculation job is being aborted.",
                },
            )
        else:
            response = Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={
                    "success": False,
                    "message": (
                        f"Cannot abort Risk Calculation job. Job status must be 'created' or 'executing', "
                        f"current job status is {openquakejob.job_status}."
                    ),
                },
            )
    else:
        response = Response(
            status=status.HTTP_400_BAD_REQUEST,
            data={"success": False, "message": "Missing 'openquakejob_id' parameter."},
        )
    return response


class EqAbortView(APIView):
    """
    API view to abort create/executing OpenQuake job.

    Reimplement eq_abort() as class-based view for throttling support.
    """

    authentication_classes = [TokenAuthentication]
    throttle_scope = "eq_abort"

    def post(self, request, format=None):
        return eq_abort(request)


# @api_view(["POST"])
# @authentication_classes([TokenAuthentication])
def eq_remove(request):
    """
    Remove an OpenQuake job from the Calculation Server. Similar to OpenquakeJobRemoveView implementation.

    Only Superuser can remove OpenquakeJob.

    Job status must be 'complete', 'aborted', or 'failed'.
    """
    openquakejob_id = request.data.get("openquakejob_id")
    if openquakejob_id:
        openquakejob = None
        if request.user.is_superuser:
            openquakejob = get_object_or_404(OpenquakeJob, pk=openquakejob_id)
        else:
            response = Response(
                status=status.HTTP_403_FORBIDDEN,
                data={"success": False, "message": "Access forbidden."},
            )
            return response
        if (
            openquakejob.status == "complete"
            or openquakejob.status == "aborted"
            or openquakejob.status == "failed"
        ):
            openquake_remove_calc_task.delay(openquakejob_id=openquakejob.id)
            response = Response(
                status=status.HTTP_200_OK,
                data={
                    "success": True,
                    "message": "Risk Calculation job is being removed.",
                },
            )
        else:
            response = Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={
                    "success": False,
                    "message": (
                        f"Cannot remove Risk Calculation job. Job status must be 'complete', "
                        f"'aborted', or 'failed', current job status is {openquakejob.job_status}."
                    ),
                },
            )
    else:
        response = Response(
            status=status.HTTP_400_BAD_REQUEST,
            data={"success": False, "message": "Missing 'openquakejob_id' parameter."},
        )
    return response


class EqRemoveView(APIView):
    """
    API view to remove an OpenQuake job from the Calculation Server.

    Reimplement eq_remove() as class-based view for throttling support.
    """

    authentication_classes = [TokenAuthentication]
    throttle_scope = "eq_remove"

    def post(self, request, format=None):
        return eq_remove(request)


# @api_view(["DELETE"])
# @authentication_classes([TokenAuthentication])
def eq_delete(request):
    """
    Delete single owned OpenquakeJob. Similar to OpenquakeJobDeleteView implementation.

    Superuser can delete any OpenquakeJob, others can only delete owned OpenquakeJob.

    Non Superuser cannot delete completed job to reduce quota usage!

    Jobs with status 'created' or 'executing' will be aborted first.
    """
    openquakejob_id = request.data.get("openquakejob_id")
    if openquakejob_id:
        openquakejob = None
        if request.user.is_superuser:
            openquakejob = get_object_or_404(OpenquakeJob, pk=openquakejob_id)
        else:
            if not user_is_superuser_or_in_groups(request.user, ["Analyst"]):
                response = Response(
                    status=status.HTTP_403_FORBIDDEN,
                    data={"success": False, "message": "Access forbidden."},
                )
                return response
            openquakejob = get_object_or_404(
                OpenquakeJob, pk=openquakejob_id, user=request.user
            )
            if openquakejob.job_status == "complete":
                response = Response(
                    status=status.HTTP_400_BAD_REQUEST,
                    data={
                        "success": False,
                        "message": "Cannot delete completed Risk Calculation job.",
                    },
                )
                return response
        if (
            openquakejob.job_status == "created"
            or openquakejob.job_status == "executing"
        ):
            openquake_abort_calc_task.delay(
                openquakejob_id=openquakejob.id, delete=True
            )
        else:
            openquakejob.delete()
        response = Response(
            status=status.HTTP_200_OK,
            data={"success": True, "message": "Risk Calculation job is being deleted."},
        )
    else:
        response = Response(
            status=status.HTTP_400_BAD_REQUEST,
            data={"success": False, "message": "Missing 'openquakejob_id' parameter."},
        )
    return response


class EqDeleteView(APIView):
    """
    API view to delete a single owned OpenquakeJob.

    Reimplement eq_delete() as class-based view for throttling support.
    """

    authentication_classes = [TokenAuthentication]
    throttle_scope = "eq_delete"

    def delete(self, request, format=None):
        return eq_delete(request)


@api_view(["GET"])
@authentication_classes([TokenAuthentication])
def eq_pml(request, openquakejob_id):
    """
    Get PML data from an OpenquakeJob. Similar to RiskMatrixDetailView implementation.

    Superuser can get PML data from any OpenquakeJob, others can only get PML data from owned OpenquakeJob.
    """
    if openquakejob_id:
        openquakejob = None
        if request.user.is_superuser:
            openquakejob = get_object_or_404(OpenquakeJob, pk=openquakejob_id)
        else:
            openquakejob = get_object_or_404(
                OpenquakeJob, pk=openquakejob_id, user=request.user
            )
        if not user_is_superuser_or_in_groups(request.user, ["Analyst"]):
            response = Response(
                status=status.HTTP_403_FORBIDDEN,
                data={"message": "Access forbidden."},
            )
            return response
        pml_data = []
        for pml in openquakejob.openquakepmls.all().order_by("return_period"):
            pml_dict = {
                "return_period": pml.return_period,
                "loss": pml.loss,
                "loss_ratio": pml.loss_ratio,
            }
            pml_data.append(pml_dict)
        response = JsonResponse(pml_data, safe=False)
    else:
        response = Response(
            status=status.HTTP_400_BAD_REQUEST,
            data={"success": False, "message": "Missing 'openquakejob_id' parameter."},
        )
    return response


@api_view(["GET"])
@authentication_classes([TokenAuthentication])
def eq_aal(request, openquakejob_id):
    """
    Get AAL data from an OpenquakeJob. Similar to RiskMatrixDetailView implementation.

    Superuser can get AAL data from any OpenquakeJob, others can only get AAL data from owned OpenquakeJob.
    """
    if openquakejob_id:
        openquakejob = None
        if request.user.is_superuser:
            openquakejob = get_object_or_404(OpenquakeJob, pk=openquakejob_id)
        else:
            openquakejob = get_object_or_404(
                OpenquakeJob, pk=openquakejob_id, user=request.user
            )
        if not user_is_superuser_or_in_groups(request.user, ["Analyst"]):
            response = Response(
                status=status.HTTP_403_FORBIDDEN,
                data={"success": False, "message": "Access forbidden."},
            )
            return response
        aal_data = []
        openquakeaals = OpenquakeAAL.objects.filter(openquakejob=openquakejob).defer(
            "provinsi__polygon", "kabupaten_kota__polygon"
        )
        for aal in openquakeaals:
            provinsi_id = aal.provinsi.id if aal.provinsi else None
            kabupaten_kota_id = aal.kabupaten_kota.id if aal.kabupaten_kota else None
            aal_dict = {
                "province": aal.province,
                "provinsi_id": provinsi_id,
                "city": aal.city,
                "kabupaten_kota_id": kabupaten_kota_id,
                "total": aal.total,
                "loss_ratio": aal.loss_ratio,
            }
            aal_data.append(aal_dict)
        response = JsonResponse(aal_data, safe=False)
    else:
        response = Response(
            status=status.HTTP_400_BAD_REQUEST,
            data={"success": False, "message": "Missing 'openquakejob_id' parameter."},
        )
    return response


@api_view(["GET"])
@authentication_classes([TokenAuthentication])
def eq_elt(request, openquakejob_id):
    """
    Get ELT file URL from an OpenquakeJob. Similar to RiskMatrixDetailView implementation.

    Superuser can get ELT file URL from any OpenquakeJob, others can only get ELT file URL from owned OpenquakeJob.
    """
    if openquakejob_id:
        openquakejob = None
        if request.user.is_superuser:
            openquakejob = get_object_or_404(OpenquakeJob, pk=openquakejob_id)
        else:
            openquakejob = get_object_or_404(
                OpenquakeJob, pk=openquakejob_id, user=request.user
            )
        if not user_is_superuser_or_in_groups(request.user, ["Analyst"]):
            response = Response(
                status=status.HTTP_403_FORBIDDEN,
                data={"success": False, "message": "Access forbidden."},
            )
            return response
        elt_file = openquakejob.result_files.all().filter(
            name="Aggregated Risk By Event (.csv)"
        )
        if elt_file:
            elt_file_url = elt_file[0].file.url
            elt_file_data = {"elt_file_url": elt_file_url}
            response = JsonResponse(elt_file_data)
        else:
            response = Response(
                status=status.HTTP_404_NOT_FOUND,
                data={"success": False, "message": "ELT file not found."},
            )
    else:
        response = Response(
            status=status.HTTP_400_BAD_REQUEST,
            data={"success": False, "message": "Missing 'openquakejob_id' parameter."},
        )
    return response


def get_calculationserver_dict(calculationserver):
    calculationserver_dict = {
        "id": calculationserver.id,
        "created": calculationserver.created,
        "updated": calculationserver.updated,
        "name": calculationserver.name,
        "enabled": calculationserver.enabled,
        "type": calculationserver.type,
        "status": calculationserver.status,
        "active": calculationserver.active,
        "last_active": calculationserver.last_active,
        "last_checked": calculationserver.last_checked,
    }
    return calculationserver_dict


@api_view(["GET"])
@authentication_classes([TokenAuthentication])
def calculation_server(request, calculationserver_id=None):
    """
    Return array of CalculationServers or single CalculationServer details.

    Only Superuser can access.
    """
    if request.user.is_superuser:
        if calculationserver_id:  # return calculationserver dict
            calculationserver = get_object_or_404(
                CalculationServer, pk=calculationserver_id
            )
            calculationserver_dict = get_calculationserver_dict(calculationserver)
            response = JsonResponse(calculationserver_dict)
        else:  # return array of calculationserver dicts
            calculationservers = CalculationServer.objects.all()
            calculationserver_data = []
            for calculationserver in calculationservers:
                calculationserver_dict = get_calculationserver_dict(calculationserver)
                calculationserver_data.append(calculationserver_dict)
            response = JsonResponse(calculationserver_data, safe=False)
    else:
        response = Response(
            status=status.HTTP_403_FORBIDDEN,
            data={"success": False, "message": "Access forbidden."},
        )
    return response
