import csv
import io
import json
import logging
import os
import shutil
import tempfile
import time
import uuid  # noqa F401
import zipfile
from decimal import Decimal
from urllib.parse import urljoin

import boto3
import magic
import requests
from botocore.exceptions import ClientError
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.contrib.gis.geos import Point
from django.core import files
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.files.base import ContentFile
from django.core.mail import mail_admins, mail_managers, send_mail
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from ai_risiko.administrasiwilayah.models import Kabupaten_Kota, Provinsi
from ai_risiko.airisiko.templatetags.airisiko_tags import airisiko_seconds_to_minutes
from config import celery_app

from .models import (
    Asset,
    AssetUpload,
    CalculationServer,
    Exposure,
    ExposureRecapitulation,
    ExposureUpload,
    OpenquakeAAL,
    OpenquakeJob,
    OpenquakePML,
    ResultFile,
)


def create_presigned_url(bucket_name, object_name, expiration=3600):
    """
    Generate a presigned URL to share an S3 object.
    """
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
    try:
        response = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": object_name},
            ExpiresIn=expiration,
        )
        return response
    except ClientError as e:
        logging.error(e)
        return None


def save_assets_csv(csv_file_path, instance):
    """
    Read an Asset .csv file and save each row as Assets.
    """
    try:
        if os.path.isfile(csv_file_path):
            accepted_mime_types = ["text/plain", "application/csv"]
            mime = magic.from_file(csv_file_path, mime=True)
            if mime in accepted_mime_types:
                with open(csv_file_path) as csv_file:
                    logging.info(f"Saving Assets from csv: {csv_file_path}")
                    # import all rows in .csv file or nothing at all
                    with transaction.atomic():
                        # determine .csv details
                        csv_delimiter = (
                            instance.csv_delimiter if instance.csv_delimiter else ","
                        )
                        csv_column_asset_name = (
                            instance.csv_column_asset_name
                            if instance.csv_column_asset_name
                            else ""
                        )
                        csv_column_asset_address = (
                            instance.csv_column_asset_address
                            if instance.csv_column_asset_address
                            else ""
                        )
                        csv_column_asset_type = (
                            instance.csv_column_asset_type
                            if instance.csv_column_asset_type
                            else ""
                        )
                        csv_column_asset_latitude = (
                            instance.csv_column_asset_latitude
                            if instance.csv_column_asset_latitude
                            else ""
                        )
                        csv_column_asset_longitude = (
                            instance.csv_column_asset_longitude
                            if instance.csv_column_asset_longitude
                            else ""
                        )
                        csv_column_asset_occupancy = (
                            instance.csv_column_asset_occupancy
                            if instance.csv_column_asset_occupancy
                            else ""
                        )
                        csv_reader = csv.DictReader(csv_file, delimiter=csv_delimiter)
                        row_count = 0
                        for row in csv_reader:
                            row_count += 1
                            asset = Asset()
                            asset.name = (
                                row[csv_column_asset_name]
                                if csv_column_asset_name
                                else ""
                            )
                            asset.address = (
                                row[csv_column_asset_address]
                                if csv_column_asset_address
                                else ""
                            )
                            asset.type = (
                                row[csv_column_asset_type]
                                if csv_column_asset_type
                                else ""
                            )
                            asset_latitude = (
                                row[csv_column_asset_latitude]
                                if csv_column_asset_latitude
                                else ""
                            )
                            asset_longitude = (
                                row[csv_column_asset_longitude]
                                if csv_column_asset_longitude
                                else ""
                            )
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
                            asset.occupancy = (
                                row[csv_column_asset_occupancy]
                                if csv_column_asset_occupancy
                                else ""
                            )
                            asset.asset_upload = instance
                            try:
                                # validate instance first
                                asset.full_clean()
                                asset.save()
                            except ValidationError as e:
                                for k, v in e.message_dict.items():
                                    error_msg = f'- WARNING row {row_count}: save error for Asset field "{k}" => {v}'
                                    logging.warning(error_msg)
                        instance.import_status = True
                        instance.save()
                        logging.info("Saving Assets from csv complete!")
                        return True
    except Exception as err:
        logging.error(f"ERROR save_assets_csv: {err}")
        instance.import_status = False
        instance.import_message = f"ERROR: {err}"
        instance.save()
        return False


def save_aal_csv(csv_file_path, openquakejob):
    """
    Read an Average Asset Losses Statistics .csv file and save each row as OpenquakeAAL.

    avg_losses-mean_x.csv in avg_losses-stats-csv.zip
    """
    try:
        if os.path.isfile(csv_file_path):
            accepted_mime_types = ["text/plain", "application/csv"]
            mime = magic.from_file(csv_file_path, mime=True)
            if mime in accepted_mime_types:
                with open(csv_file_path) as csv_file:
                    logging.info(f"Saving OpenquakeAAL from csv: {csv_file_path}")
                    # import all rows in .csv file or nothing at all
                    with transaction.atomic():
                        # skip first commented row
                        next(csv_file)
                        aal_national = float(0)
                        """
                        AAL for provinces and cities are stored in a dict with the following structure:
                        aal_province = {
                            "province_name": {
                                "provinsi": Provinsi object or None,
                                "total": float(total_aal_for_province)
                            }
                        }
                        aal_city = {
                            "city_name": {
                                "province": "province_name",
                                "kabupaten_kota": Kabupaten_Kota object or None,
                                "total": float(total_aal_for_city)
                            }
                        }
                        """
                        aal_province = {}
                        aal_city = {}
                        exposure_upload = openquakejob.exposure.exposure_upload
                        # set defaults, if exposure is created from api then exposure_upload is null!
                        column_province = "name_1"
                        column_city = "name_2"
                        column_structural = "structural"
                        column_latitude = "lat"
                        column_longitude = "lon"
                        if exposure_upload:
                            column_province = exposure_upload.csv_column_province
                            column_city = exposure_upload.csv_column_city
                            column_structural = exposure_upload.csv_column_structural
                            column_latitude = exposure_upload.csv_column_asset_latitude
                            column_longitude = (
                                exposure_upload.csv_column_asset_longitude
                            )
                        csv_reader = csv.DictReader(csv_file, delimiter=",")
                        for row in csv_reader:
                            if (
                                row[column_province]
                                and row[column_city]
                                and row[column_structural]
                                and row[column_latitude]
                                and row[column_longitude]
                            ):
                                if row[column_province] not in aal_province:
                                    aal_province[row[column_province]] = {
                                        "provinsi": None,
                                        "total": float(0),
                                    }
                                if row[column_city] not in aal_city:
                                    aal_city[row[column_city]] = {
                                        "province": row[column_province],
                                        "kabupaten_kota": None,
                                        "total": float(0),
                                    }
                                try:
                                    structural = float(
                                        row[column_structural]
                                    )  # structural in csv is 3.35449E+06
                                    aal_national += structural
                                    aal_province[row[column_province]]["total"] += (
                                        structural
                                    )
                                    aal_city[row[column_city]]["total"] += structural
                                    # query provinsi from coordinates
                                    if not aal_province[row[column_province]][
                                        "provinsi"
                                    ]:
                                        latitude = row[column_latitude]
                                        longitude = row[column_longitude]
                                        provinsi = Provinsi.objects.filter(
                                            polygon__contains=Point(
                                                float(longitude), float(latitude)
                                            )
                                        )
                                        if provinsi:
                                            aal_province[row[column_province]][
                                                "provinsi"
                                            ] = provinsi[0]
                                    # query kabupaten_kota from coordinates
                                    if not aal_city[row[column_city]]["kabupaten_kota"]:
                                        latitude = row[column_latitude]
                                        longitude = row[column_longitude]
                                        point = Point(float(longitude), float(latitude))
                                        kabupaten_kota = Kabupaten_Kota.objects.filter(
                                            polygon__contains=point
                                        ).order_by("id")
                                        if kabupaten_kota:
                                            aal_city[row[column_city]][
                                                "kabupaten_kota"
                                            ] = kabupaten_kota[0]
                                except ValueError:
                                    pass
                        # delete all existing aal data first
                        openquakejob.openquakeaals.all().delete()
                        # save national aal
                        exposurerecap_national = None
                        # get total exposure from recap
                        try:
                            exposurerecap_national = ExposureRecapitulation.objects.get(
                                exposure=openquakejob.exposure, province="", city=""
                            )
                        except ObjectDoesNotExist:
                            logging.error(
                                "FATAL ERROR save_aal_csv: National exposure total not found!"
                            )
                            return False
                        openquake_aal_national = OpenquakeAAL()
                        openquake_aal_national.openquakejob = openquakejob
                        openquake_aal_national.province = ""
                        openquake_aal_national.city = ""
                        openquake_aal_national.total = Decimal(aal_national)
                        openquake_aal_national.loss_ratio = (
                            aal_national / float(exposurerecap_national.total) * 100
                        )
                        openquake_aal_national.save()
                        # save province aal
                        exposurerecap_provinces_total = {}  # cache total from queries
                        for province, details in aal_province.items():
                            exposurerecap_province = None
                            # get total exposure from recap
                            if province not in exposurerecap_provinces_total:
                                try:
                                    exposurerecap_province = (
                                        ExposureRecapitulation.objects.get(
                                            exposure=openquakejob.exposure,
                                            province=province,
                                            city="",
                                        )
                                    )
                                    exposurerecap_provinces_total[province] = (
                                        exposurerecap_province.total
                                    )
                                except ObjectDoesNotExist:
                                    logging.error(
                                        "FATAL ERROR save_aal_csv: Province exposure total not found!"
                                    )
                                    return False
                            openquake_aal_province = OpenquakeAAL()
                            openquake_aal_province.openquakejob = openquakejob
                            openquake_aal_province.province = province
                            openquake_aal_province.city = ""
                            openquake_aal_province.provinsi = details["provinsi"]
                            openquake_aal_province.total = Decimal(details["total"])
                            openquake_aal_province.loss_ratio = (
                                details["total"]
                                / float(exposurerecap_provinces_total[province])
                                * 100
                            )
                            openquake_aal_province.save()
                        # save city aal
                        exposurerecap_city_total = {}  # cache total from queries
                        for city, details in aal_city.items():
                            exposurerecap_city = None
                            # get total exposure from recap
                            if city not in exposurerecap_city_total:
                                try:
                                    exposurerecap_city = (
                                        ExposureRecapitulation.objects.get(
                                            exposure=openquakejob.exposure,
                                            province=details["province"],
                                            city=city,
                                        )
                                    )
                                    exposurerecap_city_total[city] = (
                                        exposurerecap_city.total
                                    )
                                except ObjectDoesNotExist:
                                    logging.error(
                                        "FATAL ERROR save_aal_csv: City exposure total not found!"
                                    )
                                    return False
                            openquake_aal_city = OpenquakeAAL()
                            openquake_aal_city.openquakejob = openquakejob
                            openquake_aal_city.province = details["province"]
                            openquake_aal_city.city = city
                            openquake_aal_city.kabupaten_kota = details[
                                "kabupaten_kota"
                            ]
                            openquake_aal_city.total = Decimal(details["total"])
                            openquake_aal_city.loss_ratio = (
                                details["total"]
                                / float(exposurerecap_city_total[city])
                                * 100
                            )
                            openquake_aal_city.save()
                        logging.info("Saving OpenquakeAAL from csv complete!")
                        return True
    except Exception as err:
        logging.error(f"FATAL ERROR save_aal_csv: {err}")
        return False


def save_pml_csv(csv_file_path, openquakejob):
    """
    Read an Aggregate Risk Curves Statistics .csv file and save each row where stat=mean as OpenquakePML.
    """
    try:
        if os.path.isfile(csv_file_path):
            accepted_mime_types = ["text/plain", "application/csv"]
            mime = magic.from_file(csv_file_path, mime=True)
            if mime in accepted_mime_types:
                with open(csv_file_path) as csv_file:
                    logging.info(f"Saving OpenquakePML from csv: {csv_file_path}")
                    # import all rows in .csv file or nothing at all
                    with transaction.atomic():
                        exposurerecap_national = None
                        # get total exposure from recap
                        try:
                            exposurerecap_national = ExposureRecapitulation.objects.get(
                                exposure=openquakejob.exposure, province="", city=""
                            )
                        except ObjectDoesNotExist:
                            logging.error(
                                "FATAL ERROR save_pml_csv: National exposure total not found!"
                            )
                            return False
                        # delete all existing pml data first
                        openquakejob.openquakepmls.all().delete()
                        # skip first commented row
                        next(csv_file)
                        csv_reader = csv.DictReader(csv_file, delimiter=",")
                        for row in csv_reader:
                            if row["stat"] == "mean":
                                openquakepml = OpenquakePML()
                                openquakepml.openquakejob = openquakejob
                                openquakepml.return_period = row["return_period"]
                                openquakepml.loss = row["loss"]
                                openquakepml.loss_ratio = (
                                    float(row["loss"])
                                    / float(exposurerecap_national.total)
                                    * 100
                                )
                                openquakepml.save()
                        logging.info("Saving OpenquakePML from csv complete!")
                        return True
    except Exception as err:
        logging.error(f"FATAL ERROR save_pml_csv: {err}")
        return False


@celery_app.task(bind=True, track_started=True, name="exposureupload_delete_task")
def exposureupload_delete_task(self, exposureupload_id):
    """
    Delete an ExposureUpload and related Asset, Exposure, ExposureRecapitulation asynchronously.
    """
    task_id = self.request.id
    task_state = self.AsyncResult(task_id).state
    logging.info(
        f"+++ exposureupload_delete_task task ID/state: {task_id}/{task_state}"
    )
    exposureupload = ExposureUpload.objects.get(id=exposureupload_id)
    exposureupload.delete()


@celery_app.task(bind=True, track_started=True, name="exposure_recapitulate_task")
def exposure_recapitulate_task(self, exposure_id):
    """
    Recapitulate the total Exposure structural value for national, province, and city levels.

    Existing ExposureRecapitulation for the Exposure will be deleted first.
    """
    task_id = self.request.id
    task_state = self.AsyncResult(task_id).state
    logging.info(
        f"+++ exposure_recapitulate_task task ID/state: {task_id}/{task_state}"
    )
    exposure = Exposure.objects.get(id=exposure_id)
    logging.info(f"Recapitulating Exposure data for: {exposure}")
    exposure_total_national = float(0)
    exposure_total_province = {}
    exposure_total_city = {}
    for asset in exposure.assets.all():
        # 202609 use administrasi wilayah data for province name, city name if available
        # see openquake_generate_job_archive_file()
        asset_province = asset.province
        asset_city = asset.city
        if asset.kabupaten_kota:
            asset_province = asset.kabupaten_kota.provinsi.nama
            # use kemendagri data if available
            asset_city = (
                asset.kabupaten_kota.nama_kemendagri
                if asset.kabupaten_kota.nama_kemendagri
                else asset.kabupaten_kota.nama
            )
        if asset_province and asset_city and asset.structural:
            if asset_province not in exposure_total_province:
                exposure_total_province[asset_province] = float(0)
            if asset_city not in exposure_total_city:
                exposure_total_city[asset_city] = {
                    "province": asset_province,
                    "total": float(0),
                }
            try:
                structural = float(asset.structural)
                exposure_total_national += structural
                exposure_total_province[asset_province] += structural
                exposure_total_city[asset_city]["total"] += structural
            except ValueError:
                pass
    # delete all existing recapitulation data first
    exposure.exposurerecapitulations.all().delete()
    # save national exposure total
    exposure_recapitulation_national = ExposureRecapitulation()
    exposure_recapitulation_national.exposure = exposure
    exposure_recapitulation_national.province = ""
    exposure_recapitulation_national.city = ""
    exposure_recapitulation_national.total = Decimal(exposure_total_national)
    exposure_recapitulation_national.save()
    # save province exposure total
    for province, exposure_total in exposure_total_province.items():
        exposure_recapitulation_province = ExposureRecapitulation()
        exposure_recapitulation_province.exposure = exposure
        exposure_recapitulation_province.province = province
        exposure_recapitulation_province.city = ""
        exposure_recapitulation_province.total = Decimal(exposure_total)
        exposure_recapitulation_province.save()
    # save city exposure total
    for city, details in exposure_total_city.items():
        exposure_recapitulation_city = ExposureRecapitulation()
        exposure_recapitulation_city.exposure = exposure
        exposure_recapitulation_city.province = details["province"]
        exposure_recapitulation_city.city = city
        exposure_recapitulation_city.total = Decimal(details["total"])
        exposure_recapitulation_city.save()
    logging.info("Recapitulating Exposure data complete!")


def save_exposure_csv(csv_file_path, instance):
    """
    Read an Exposure .csv file and save each row as Assets.

    All saved Assets belong to a M2M relation with an Exposure.
    """
    try:
        if os.path.isfile(csv_file_path):
            accepted_mime_types = ["text/plain", "application/csv"]
            mime = magic.from_file(csv_file_path, mime=True)
            if mime in accepted_mime_types:
                with open(csv_file_path) as csv_file:
                    logging.info(f"Saving Exposure from csv: {csv_file_path}")
                    # import all rows in .csv file or nothing at all
                    with transaction.atomic():
                        # create new exposure to contain imported assets
                        exposure = Exposure()
                        exposure.name = instance.name
                        exposure.exposure_upload = instance
                        exposure.save()
                        # determine .csv details
                        csv_delimiter = (
                            instance.csv_delimiter if instance.csv_delimiter else ","
                        )
                        csv_column_asset_name = (
                            instance.csv_column_asset_name
                            if instance.csv_column_asset_name
                            else ""
                        )
                        csv_column_asset_address = (
                            instance.csv_column_asset_address
                            if instance.csv_column_asset_address
                            else ""
                        )
                        csv_column_asset_type = (
                            instance.csv_column_asset_type
                            if instance.csv_column_asset_type
                            else ""
                        )
                        csv_column_asset_latitude = (
                            instance.csv_column_asset_latitude
                            if instance.csv_column_asset_latitude
                            else ""
                        )
                        csv_column_asset_longitude = (
                            instance.csv_column_asset_longitude
                            if instance.csv_column_asset_longitude
                            else ""
                        )
                        csv_column_asset_occupancy = (
                            instance.csv_column_asset_occupancy
                            if instance.csv_column_asset_occupancy
                            else ""
                        )
                        # extra exposure fields (based on exposure.csv)
                        csv_column_csv_id = (
                            instance.csv_column_csv_id
                            if instance.csv_column_csv_id
                            else ""
                        )
                        csv_column_asset_id = (
                            instance.csv_column_asset_id
                            if instance.csv_column_asset_id
                            else ""
                        )
                        csv_column_taxonomy = (
                            instance.csv_column_taxonomy
                            if instance.csv_column_taxonomy
                            else ""
                        )
                        csv_column_structural = (
                            instance.csv_column_structural
                            if instance.csv_column_structural
                            else ""
                        )
                        csv_column_occupancy_description = (
                            instance.csv_column_occupancy_description
                            if instance.csv_column_occupancy_description
                            else ""
                        )
                        csv_column_city = (
                            instance.csv_column_city if instance.csv_column_city else ""
                        )
                        csv_column_city_code = (
                            instance.csv_column_city_code
                            if instance.csv_column_city_code
                            else ""
                        )
                        csv_column_province = (
                            instance.csv_column_province
                            if instance.csv_column_province
                            else ""
                        )
                        csv_column_material = (
                            instance.csv_column_material
                            if instance.csv_column_material
                            else ""
                        )
                        csv_column_llrs = (
                            instance.csv_column_llrs if instance.csv_column_llrs else ""
                        )
                        csv_column_code = (
                            instance.csv_column_code if instance.csv_column_code else ""
                        )
                        csv_column_ductility = (
                            instance.csv_column_ductility
                            if instance.csv_column_ductility
                            else ""
                        )
                        csv_column_height = (
                            instance.csv_column_height
                            if instance.csv_column_height
                            else ""
                        )
                        csv_column_night = (
                            instance.csv_column_night
                            if instance.csv_column_night
                            else ""
                        )
                        csv_column_group = (
                            instance.csv_column_group
                            if instance.csv_column_group
                            else ""
                        )
                        csv_reader = csv.DictReader(csv_file, delimiter=csv_delimiter)
                        rows = list(csv_reader)
                        # enforce unique csv_id across the batch
                        seen_csv_ids = set()
                        duplicate_csv_ids = set()
                        for row in rows:
                            csv_id = row[csv_column_csv_id] if csv_column_csv_id else ""
                            if csv_id:
                                if csv_id in seen_csv_ids:
                                    duplicate_csv_ids.add(csv_id)
                                seen_csv_ids.add(csv_id)
                        if duplicate_csv_ids:
                            raise ValueError(
                                "Duplicate csv_id value(s) found in the Exposure .csv: "
                                f"{', '.join(sorted(duplicate_csv_ids))}. csv_id must be unique."
                            )
                        row_count = 0
                        for row in rows:
                            row_count += 1
                            asset = Asset()
                            asset.name = (
                                row[csv_column_asset_name]
                                if csv_column_asset_name
                                else ""
                            )
                            asset.address = (
                                row[csv_column_asset_address]
                                if csv_column_asset_address
                                else ""
                            )
                            asset.type = (
                                row[csv_column_asset_type]
                                if csv_column_asset_type
                                else ""
                            )
                            asset_latitude = (
                                row[csv_column_asset_latitude]
                                if csv_column_asset_latitude
                                else ""
                            )
                            asset_longitude = (
                                row[csv_column_asset_longitude]
                                if csv_column_asset_longitude
                                else ""
                            )
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
                            asset.occupancy = (
                                row[csv_column_asset_occupancy]
                                if csv_column_asset_occupancy
                                else ""
                            )
                            # extra exposure fields (based on exposure.csv)
                            asset.csv_id = (
                                row[csv_column_csv_id] if csv_column_csv_id else ""
                            )
                            asset.asset_id = (
                                row[csv_column_asset_id] if csv_column_asset_id else ""
                            )
                            asset.taxonomy = (
                                row[csv_column_taxonomy] if csv_column_taxonomy else ""
                            )
                            asset.structural = (
                                row[csv_column_structural]
                                if csv_column_structural
                                else ""
                            )
                            asset.occupancy_description = (
                                row[csv_column_occupancy_description]
                                if csv_column_occupancy_description
                                else ""
                            )
                            asset.city = row[csv_column_city] if csv_column_city else ""
                            asset.province = (
                                row[csv_column_province] if csv_column_province else ""
                            )
                            asset.city_code = (
                                row[csv_column_city_code]
                                if csv_column_city_code
                                else ""
                            )
                            asset.material = (
                                row[csv_column_material] if csv_column_material else ""
                            )
                            asset.llrs = row[csv_column_llrs] if csv_column_llrs else ""
                            asset.code = row[csv_column_code] if csv_column_code else ""
                            asset.ductility = (
                                row[csv_column_ductility]
                                if csv_column_ductility
                                else ""
                            )
                            asset.height = (
                                row[csv_column_height] if csv_column_height else ""
                            )
                            asset.night = (
                                row[csv_column_night] if csv_column_night else ""
                            )
                            asset.group = (
                                row[csv_column_group] if csv_column_group else ""
                            )
                            asset.exposure_upload = instance
                            try:
                                # validate instance first
                                asset.full_clean()
                                asset.save()
                                # add asset to exposure m2m relationship
                                exposure.assets.add(asset)
                            except ValidationError as e:
                                for k, v in e.message_dict.items():
                                    error_msg = f'- WARNING row {row_count}: save error for Asset field "{k}" => {v}'
                                    logging.warning(error_msg)
                        instance.import_status = True
                        instance.save()
                        exposure.save()
                        logging.info("Saving Exposure from csv complete!")
                        # call synchronously since operation is atomic
                        exposure_recapitulate_task.s(exposure_id=exposure.id).apply()
                        return True
    except Exception as err:
        logging.error(f"ERROR save_exposure_csv: {err}")
        instance.import_status = False
        instance.import_message = f"ERROR: {err}"
        instance.save()
        return False


def start_aws_calculation_server(calculationserver, purpose=""):
    """
    Start a Calculation Server on AWS.

    On successful start notify the admins via email.
    """
    aws_success = False
    aws_error = False
    if (
        settings.EC2_AWS_REGION
        and settings.EC2_AWS_ACCESS_KEY_ID
        and settings.EC2_AWS_SECRET_ACCESS_KEY
    ):
        try:
            aws_config = json.loads(calculationserver.notes)
            instance_id = aws_config["AWS"]["instance_id"]
            logging.info("Server is on AWS, try to start it up...")
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
                response = ec2.start_instances(InstanceIds=[instance_id], DryRun=False)
                if response:
                    aws_success = True
            except ClientError as e:
                logging.error(f"ERROR start_aws_calculation_server: {e}")
                aws_error = True
        except Exception as err:
            logging.error(f"ERROR start_aws_calculation_server: {err}")
            aws_error = True
    else:
        logging.error("ERROR start_aws_calculation_server: Missing AWS EC2 credentials!")
        aws_error = True
    if aws_success:
        logging.info(
            f"Successfully started Calculation Server on AWS: {calculationserver}"
        )
        mail_admins_task.delay(
            subject=f'[BACKEND TASK] Started AWS Calculation Server "{calculationserver}"',
            message=f'The calculation server "{calculationserver}" has been started for: {purpose}',
        )
        return True
    if aws_error:
        logging.error(
            f"ERROR start_aws_calculation_server: "
            f"Failed starting Calculation Server on AWS: {calculationserver}"
        )
        return False


def get_calculation_server(type, purpose=""):
    """
    Get a calculation server that is ready.

    If the server is on AWS then try to start it up.
    """
    server = None
    server_candidates = []
    # look in table first
    if CalculationServer.objects.count():
        calculation_servers = (
            CalculationServer.objects.filter(
                type=type,
                enabled=True,
            )
            .exclude(status="WORKING")
            .order_by("?")
        )  # randomize server returned
        for calculation_server in calculation_servers:
            logging.info(
                f"Adding {type} server candidate from the database: {calculation_server}"
            )
            server_candidates.append(
                {
                    "instance": calculation_server,
                    "base_url": calculation_server.base_url,
                    "user_login": calculation_server.user_login,
                    "user_password": calculation_server.user_password,
                    "calculation_server_started": False,
                }
            )
    else:  # look in config
        if type == "openquake":
            logging.info(
                f"Adding default {type} server candidate: {settings.OPENQUAKE_BASE_URL}"
            )
            server_candidates.append(
                {
                    "base_url": settings.OPENQUAKE_BASE_URL,
                    "user_login": settings.OPENQUAKE_ADMIN_LOGIN,
                    "user_password": settings.OPENQUAKE_ADMIN_PASSWORD,
                }
            )
    for server_candidate in server_candidates:
        page = ""
        tries = 0
        # try waiting until remote server is ready...
        while page == "":
            try:
                tries += 1
                logging.info(
                    f"Server connection to {server_candidate['base_url']} try number: {tries}"
                )
                page = requests.get(
                    server_candidate["base_url"],
                    timeout=settings.REQUESTS_CONNECTION_TIMEOUT,
                )
                page.raise_for_status()
                break
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.HTTPError,  # handle HTTPError 502 bad gateway
            ) as err:
                # reset page since HTTPError 502 will set page as Response [502]
                page = ""
                # exit if max connection tries reached
                if tries == settings.REQUESTS_MAX_CONNECTION_TRIES:
                    logging.info("Max connection tries reached for server.")
                    break
                # try to start up calculation server on aws
                if "instance" in server_candidate:
                    if "AWS" in server_candidate["instance"].notes:
                        if not server_candidate["calculation_server_started"]:
                            if start_aws_calculation_server(
                                server_candidate["instance"],
                                purpose,
                            ):
                                server_candidate["calculation_server_started"] = True
                                # reset tries to give server more time to complete start up
                                logging.info(
                                    "Server is being started, resetting try number to 0."
                                )
                                tries = 0
                logging.warning(err)
                logging.info("Connection refused by the server...")
                logging.info(f"Sleeping for {settings.REQUESTS_SLEEP_TIME} seconds...")
                logging.info("Zzz...")
                time.sleep(settings.REQUESTS_SLEEP_TIME)
                logging.info("Now try again...")
                continue
        if page:
            # found server that is ready
            server = server_candidate
            break
    return server


def get_openquakejob_detail_url(openquakejob):
    """
    Construct URL to OpenquakeJob detail page.
    """
    url = "https://ai.risiko.id{}".format(
        reverse("dashboard:openquakejob-detail", kwargs={"pk": openquakejob.id})
    )
    return url


def openquake_authenticate(session_obj, base_url, user_login, user_password):
    """
    Create an authenticated session with OpenQuake.
    """
    login_url = urljoin(base_url, settings.OPENQUAKE_LOGIN_ENDPOINT)
    try:
        logging.info(f"OpenQuake authenticate session: {login_url}")
        resp = session_obj.post(
            login_url,
            data={
                "username": user_login,
                "password": user_password,
            },
        )
        resp.raise_for_status()
    except requests.exceptions.HTTPError as err:
        logging.error(f"FATAL ERROR openquake_authenticate: Failed to authenticate OpenQuake user! ({err})")
        return False
    logging.info("OpenQuake authentication successful!")
    return session_obj


def openquake_get_job_status(session_obj, base_url, job_id):
    """
    Get calculation job details from OpenQuake.
    """
    job_status_url = urljoin(
        base_url,
        settings.OPENQUAKE_JOB_STATUS_ENDPOINT.format(job_id),
    )
    try:
        logging.info(f"OpenQuake getting job status: {job_status_url}")
        resp = session_obj.get(job_status_url)
        resp.raise_for_status()
    except requests.exceptions.HTTPError as err:
        logging.error(f"FATAL ERROR openquake_get_job_status: Failed to get job {job_id} status! ({err})")
        return False
    if resp.status_code == requests.codes.ok:
        job_status = json.loads(resp.text)
        return job_status


def openquake_get_job_log(session_obj, base_url, job_id):
    """
    Get calculation job log from OpenQuake.
    """
    job_log_url = urljoin(
        base_url,
        settings.OPENQUAKE_JOB_LOG_ENDPOINT.format(job_id),
    )
    try:
        logging.info(f"OpenQuake getting job log: {job_log_url}")
        resp = session_obj.get(job_log_url)
        resp.raise_for_status()
    except requests.exceptions.HTTPError as err:
        logging.error(f"FATAL ERROR openquake_get_job_log: Failed to get job {job_id} log! ({err})")
        return False
    if resp.status_code == requests.codes.ok:
        job_log = json.loads(resp.text)
        return job_log


def openquake_get_job_traceback(session_obj, base_url, job_id):
    """
    202607 Get calculation job traceback from OpenQuake.
    """
    job_traceback_url = urljoin(
        base_url,
        settings.OPENQUAKE_JOB_TRACEBACK_ENDPOINT.format(job_id),
    )
    try:
        logging.info(f"OpenQuake getting job traceback: {job_traceback_url}")
        resp = session_obj.get(job_traceback_url)
        resp.raise_for_status()
    except requests.exceptions.HTTPError as err:
        logging.error(f"FATAL ERROR openquake_get_job_traceback: Failed to get job {job_id} traceback! ({err})")
        return False
    if resp.status_code == requests.codes.ok:
        job_traceback = json.loads(resp.text)
        return job_traceback


def openquake_get_job_results(session_obj, base_url, job_id):
    """
    Get calculation job results from OpenQuake.
    """
    job_results_url = urljoin(
        base_url,
        settings.OPENQUAKE_JOB_RESULTS_ENDPOINT.format(job_id),
    )
    try:
        logging.info(f"OpenQuake getting job results: {job_results_url}")
        resp = session_obj.get(job_results_url)
        resp.raise_for_status()
    except requests.exceptions.HTTPError as err:
        logging.error(f"FATAL ERROR openquake_get_job_results: Failed to get job {job_id} results! ({err})")
        return False
    if resp.status_code == requests.codes.ok:
        job_results = json.loads(resp.text)
        return job_results


def openquake_get_job_results_files(
    session_obj, base_url, job_results, job_id, openquakejob
):
    """
    Get calculation job output files from OpenQuake.
    """
    for result_file in job_results:
        result_id = result_file["id"]
        result_name = result_file["name"]
        result_type = result_file["type"]
        result_outtypes = result_file["outtypes"]
        # download all output types
        for result_outtype in result_outtypes:
            result_file_url = urljoin(
                base_url,
                settings.OPENQUAKE_JOB_RESULTS_OUTPUT_ENDPOINT.format(
                    result_id,
                    result_outtype,
                ),
            )
            file_name = f"output_{result_id}_{result_type}_{openquakejob.id}_{job_id}.{result_outtype}"
            # special case for aal outputs are zipped csv
            if result_type == "avg_losses-rlzs" or result_type == "avg_losses-stats":
                file_name = f"{file_name}.zip"
            try:
                logging.info(
                    f"OpenQuake start downloading job {job_id} result file {file_name} from: {result_file_url}"
                )
                resp = session_obj.get(result_file_url, stream=True)
                resp.raise_for_status()
            except requests.exceptions.HTTPError as err:
                logging.error(
                    f"ERROR openquake_get_job_results_files: "
                    f"Failed to download job {job_id} result file {file_name}! ({err})"
                )
            if resp.status_code == requests.codes.ok:
                try:
                    with tempfile.NamedTemporaryFile(delete=False) as temp:
                        for chunk in resp.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                temp.write(chunk)
                        temp.flush()
                        temp.seek(0)
                        temp_file = files.File(
                            temp,
                            name=file_name,
                        )
                        result_file = ResultFile()
                        result_file.name = f"{result_name} (.{result_outtype})"
                        result_file.file = temp_file
                        result_file.save()
                        openquakejob.result_files.add(result_file)
                        openquakejob.save()
                        logging.info(
                            f"Job {job_id} result file {file_name} downloaded successfully!"
                        )
                finally:
                    os.unlink(temp.name)


def openquake_get_job_datastore_file(session_obj, base_url, job_id, openquakejob):
    """
    Get calculation job HDF5 datastore file from OpenQuake.
    """
    datastore_file_url = urljoin(
        base_url,
        settings.OPENQUAKE_JOB_RESULTS_DATASTORE_ENDPOINT.format(job_id),
    )
    try:
        logging.info(
            f"OpenQuake start downloading job {job_id} datastore file from: {datastore_file_url}"
        )
        resp = session_obj.get(datastore_file_url, stream=True)
        resp.raise_for_status()
    except requests.exceptions.HTTPError as err:
        logging.error(
            f"FATAL ERROR openquake_get_job_datastore_file: Failed to download job {job_id} datastore file! ({err})"
        )
        return False
    if resp.status_code == requests.codes.ok:
        file_saved = False
        try:
            with tempfile.NamedTemporaryFile(delete=False) as temp:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):  # 1MB chunks
                    if chunk:
                        temp.write(chunk)
                temp.flush()
                temp.seek(0)
                # random_suffix = str(uuid.uuid4())[:8]
                # file_name = f"calc_{openquakejob.id}_{job_id}_{random_suffix}.hdf5"
                file_name = f"calc_{openquakejob.id}_{job_id}.hdf5"
                temp_file = files.File(
                    temp,
                    name=file_name,
                )
                openquakejob.job_results_datastore_file = temp_file
                openquakejob.save()
                file_saved = True
                logging.info(f"Job {job_id} datastore file downloaded successfully!")
        finally:
            os.unlink(temp.name)
            if file_saved:
                return True


def openquake_abort_job(session_obj, base_url, job_id):
    """
    Abort a calculation job from OpenQuake.
    """
    abort_url = urljoin(base_url, settings.OPENQUAKE_JOB_ABORT_ENDPOINT.format(job_id))
    try:
        logging.info(f"OpenQuake aborting job: {abort_url}")
        resp = session_obj.post(
            abort_url,
            data={},
        )
        resp.raise_for_status()
    except requests.exceptions.HTTPError as err:
        logging.error(
            f"FATAL ERROR openquake_abort_job: Failed to POST OpenQuake job abort request! ({err})"
        )
        return False
    if resp.status_code == requests.codes.ok:
        job = json.loads(resp.text)
        if "success" in job:
            logging.info(f"Job {job_id} aborted!")
            return True
        elif "error" in job:
            logging.error(f"FATAL ERROR openquake_abort_job: Failed to abort job {job_id}: {job['error']}")
            return False


def openquake_remove_job(session_obj, base_url, job_id):
    """
    Remove a calculation job from OpenQuake.
    """
    remove_url = urljoin(
        base_url, settings.OPENQUAKE_JOB_REMOVE_ENDPOINT.format(job_id)
    )
    try:
        logging.info(f"OpenQuake removing job: {remove_url}")
        resp = session_obj.post(
            remove_url,
            data={},
        )
        resp.raise_for_status()
    except requests.exceptions.HTTPError as err:
        logging.error(
            f"FATAL ERROR openquake_remove_job: Failed to POST OpenQuake job remove request! ({err})"
        )
        return False
    if resp.status_code == requests.codes.ok:
        logging.info(f"Job {job_id} removed!")
        return True


def openquake_generate_job_archive_file(openquakejob):
    """
    Generate an OpenQuake job archive file from Exposure Assets.
    """
    job_archive_file = None
    logging.info(
        f"OpenQuake generating job archive file for openquakejob {openquakejob.id}"
    )
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".csv", newline="", mode="w", delete=False
        ) as tempcsv:
            delimiter = ","
            if (
                openquakejob.exposure.exposure_upload
                and openquakejob.exposure.exposure_upload.csv_delimiter
            ):
                delimiter = openquakejob.exposure.exposure_upload.csv_delimiter
            writer = csv.writer(tempcsv, delimiter=delimiter)
            writer.writerow(
                [
                    "id",
                    "lon",
                    "lat",
                    "taxonomy",
                    "number",
                    "structural",
                    "night",
                    "material",
                    "llrs",
                    "code",
                    "height",
                    "occupancy",
                    "name",
                    "name_1",
                    "id_1",
                    "name_2",
                ]
            )
            for asset in openquakejob.exposure.assets.all():
                # 202609 use administrasi wilayah data for province name, city name, and city_code if available
                asset_province = asset.province
                asset_city_code = asset.city_code
                asset_city = asset.city
                if asset.kabupaten_kota:
                    asset_province = asset.kabupaten_kota.provinsi.nama
                    # use kemendagri data if available
                    asset_city_code = (
                        asset.kabupaten_kota.id_kemendagri
                        if asset.kabupaten_kota.id_kemendagri
                        else asset.kabupaten_kota.id
                    )
                    asset_city = (
                        asset.kabupaten_kota.nama_kemendagri
                        if asset.kabupaten_kota.nama_kemendagri
                        else asset.kabupaten_kota.nama
                    )
                writer.writerow(
                    [
                        asset.csv_id,
                        asset.point[0],
                        asset.point[1],
                        asset.taxonomy,
                        asset.asset_id,
                        asset.structural,
                        asset.night,
                        asset.material,
                        asset.llrs,
                        asset.code,
                        asset.height,
                        asset.occupancy,
                        asset.name,
                        asset_province,
                        asset_city_code,
                        asset_city,
                    ]
                )
            # need to flush csv file or content will be cut off/incomplete!
            tempcsv.flush()
            mem_zip = io.BytesIO()
            files_to_zip = []
            zip_file_paths = [
                "job.ini",
                "EXPOSURE/ATMAJA_22_ID_RES_COMP/exposure_model.xml",
                # "EXPOSURE/ATMAJA_22_ID_RES_COMP/Exposure_Res_All_Indonesia.csv",
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
            # replace openquakejobtemplate exposure csv above with generated csv
            zipi_exposure_csv = zipfile.ZipInfo()
            zipi_exposure_csv.filename = (
                "EXPOSURE/ATMAJA_22_ID_RES_COMP/Exposure_Res_All_Indonesia.csv"
            )
            zipi_exposure_csv.compress_type = zipfile.ZIP_DEFLATED
            files_to_zip.append((zipi_exposure_csv, tempcsv.name))
            for zip_file_path in zip_file_paths:
                zipi = zipfile.ZipInfo()
                zipi.filename = zip_file_path
                zipi.compress_type = zipfile.ZIP_DEFLATED
                files_to_zip.append(
                    (
                        zipi,
                        os.path.join(
                            settings.STATICFILES_DIRS[0],
                            "openquakejobtemplate",
                            "v1",
                            zip_file_path,
                        ),
                    ),
                )
            ZIP_COMPRESSION_LEVEL = 5
            with zipfile.ZipFile(
                mem_zip,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=ZIP_COMPRESSION_LEVEL,
            ) as zf:
                for f in files_to_zip:
                    with open(f[1]) as fh:
                        zf.writestr(f[0], fh.read())
            full_zip_in_memory = mem_zip.getvalue()
            file_name = f"job_{openquakejob.id}.zip"
            job_archive_file = files.File(ContentFile(full_zip_in_memory, file_name))
    except Exception as err:
        logging.error(f"ERROR openquake_generate_job_archive_file: {err}")
    finally:
        os.unlink(tempcsv.name)
    return job_archive_file


@celery_app.task(name="send_mail_task")
def send_mail_task(subject, message, recipient_list):
    """
    Send an email.
    """
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        recipient_list,
        fail_silently=False,
    )


@celery_app.task(name="mail_admins_task")
def mail_admins_task(subject, message):
    """
    Send an email to site Admins defined in settings.ADMINS.
    """
    mail_admins(subject, message, fail_silently=False)


@celery_app.task(name="mail_managers_task")
def mail_managers_task(subject, message):
    """
    Send an email to site Managers defined in settings.MANAGERS.
    """
    mail_managers(subject, message, fail_silently=False)


def send_mail_notification(instance, subject, message, managers_only=False):
    """
    Send async email notification to Site Managers and Job owners.

    Optionally send email notifications to site Managers only.
    """
    recipient_list = []
    if settings.MANAGERS:
        recipient_list = [manager[1] for manager in settings.MANAGERS]
    if (
        not managers_only
        and hasattr(instance, "user")
        and instance.user
        and instance.user.email
    ):
        recipient_list.append(instance.user.email)
    if recipient_list:
        if settings.EMAIL_SUBJECT_PREFIX:
            subject = f"{settings.EMAIL_SUBJECT_PREFIX}{subject}"
        send_mail_task.delay(
            subject=subject,
            message=message,
            recipient_list=recipient_list,
        )


@celery_app.task(name="import_asset_csv_task")
def import_asset_csv_task(upload_id, is_exposure=False):
    """
    Import .csv file rows as Assets. Also accepts Exposure .csv.

    Handles .zip or .csv uploaded files to local storage or AWS bucket.
    """
    csv_file_path = None
    zip_extract_dir = None
    save_success = False
    if is_exposure:
        instance = ExposureUpload.objects.get(id=upload_id)
    else:
        instance = AssetUpload.objects.get(id=upload_id)
    if instance.file.name.lower().endswith(".zip"):
        if settings.AWS_STORAGE_BUCKET_NAME:  # in production environment
            file_url = instance.file.url
            logging.info(f"Downloading zip file from AWS: {file_url}")
            # download media files in AWS bucket for local operations
            response = requests.get(file_url)
            if response.status_code == requests.codes.ok:
                # extract .zip file to temporary directory
                zip_file = zipfile.ZipFile(io.BytesIO(response.content))
                with tempfile.TemporaryDirectory() as temp_extract_dir:
                    logging.info(
                        f"Start extracting downloaded zip file to temporary directory: {temp_extract_dir}"
                    )
                    zip_file.extractall(temp_extract_dir)
                    csv_files = [
                        os.path.join(temp_extract_dir, f)
                        for f in os.listdir(temp_extract_dir)
                        if f.lower().endswith(".csv")
                    ]
                    # search for extracted .csv files
                    if csv_files:
                        # only select first csv file found
                        csv_file_path = csv_files[0]
                        if is_exposure:
                            save_success = save_exposure_csv(csv_file_path, instance)
                        else:
                            save_success = save_assets_csv(csv_file_path, instance)
        else:  # in local environment
            # extract to /media/assetupload/filename.zip_extract/
            zip_extract_dir = os.path.join(
                os.path.dirname(instance.file.path),
                "{}_{}".format(os.path.basename(instance.file.path), "extract"),
            )
            with zipfile.ZipFile(instance.file.path, "r") as zip_obj:
                try:
                    if not os.path.isdir(zip_extract_dir):
                        os.mkdir(zip_extract_dir)
                except Exception as err:
                    logging.error(f"ERROR import_asset_csv_task: {err}")
                logging.info(
                    f"Start extracting local zip file to directory: {zip_extract_dir}"
                )
                zip_obj.extractall(zip_extract_dir)
                csv_files = [
                    os.path.join(zip_extract_dir, f)
                    for f in os.listdir(zip_extract_dir)
                    if f.lower().endswith(".csv")
                ]
                if csv_files:
                    csv_file_path = csv_files[0]
                    if is_exposure:
                        save_success = save_exposure_csv(csv_file_path, instance)
                    else:
                        save_success = save_assets_csv(csv_file_path, instance)
                shutil.rmtree(zip_extract_dir)
    elif instance.file.name.lower().endswith(".csv"):
        if settings.AWS_STORAGE_BUCKET_NAME:
            file_url = instance.file.url
            logging.info(f"Downloading csv file from AWS: {file_url}")
            response = requests.get(file_url, stream=True)
            if response.status_code == requests.codes.ok:
                try:
                    with tempfile.NamedTemporaryFile(
                        suffix=".csv", delete=False
                    ) as temp:
                        for chunk in response.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                temp.write(chunk)
                        temp.flush()
                        temp.seek(0)
                    # with open(temp.name) as csvfile:
                    #     reader = csv.reader(csvfile)
                    #     for row in reader:
                    #         print(row)
                    if is_exposure:
                        save_success = save_exposure_csv(temp.name, instance)
                    else:
                        save_success = save_assets_csv(temp.name, instance)
                finally:
                    os.unlink(temp.name)
        else:
            csv_file_path = instance.file.path
            if is_exposure:
                save_success = save_exposure_csv(csv_file_path, instance)
            else:
                save_success = save_assets_csv(csv_file_path, instance)
    imported = "Assets"
    if is_exposure:
        imported = "Exposure"
    subject = f'{imported} successfully imported from "{instance.name}" CSV file'
    message = f'The {imported} from "{instance.name}" CSV file have been imported.'
    if not save_success:
        subject = f'Failed to import {imported} from "{instance.name}" CSV file'
        message = (
            f'The {imported} from "{instance.name}" CSV file have not been imported.'
        )
    send_mail_notification(
        instance,
        subject,
        message,
    )


@celery_app.task(name="add_task")
def add_task(x, y):
    """ """
    return x + y


@celery_app.task(name="multiply_task")
def multiply_task(x, y):
    """ """
    return x * y


@celery_app.task(bind=True, track_started=True, name="openquake_recapitulate_aal_task")
def openquake_recapitulate_aal_task(self, openquakejob_id):
    """
    Import an OpenquakeJob's Average Asset Losses Statistics zipped .csv file rows as OpenquakeAALs.

    Handles zipped .csv uploaded files to local storage or AWS bucket.
    """
    task_id = self.request.id
    task_state = self.AsyncResult(task_id).state
    logging.info(
        f"+++ openquake_recapitulate_aal_task task ID/state: {task_id}/{task_state}"
    )
    openquakejob = OpenquakeJob.objects.get(id=openquakejob_id)
    result_file = openquakejob.result_files.all().filter(
        name="Average Asset Losses Statistics (.csv)"
    )
    if openquakejob.exposure and result_file:
        aal_csv_zip = result_file[0]
        if settings.AWS_STORAGE_BUCKET_NAME:  # in production environment
            file_url = aal_csv_zip.file.url
            logging.info(f"Downloading zip file from AWS: {file_url}")
            response = requests.get(file_url)
            if response.status_code == requests.codes.ok:
                zip_file = zipfile.ZipFile(io.BytesIO(response.content))
                with tempfile.TemporaryDirectory() as temp_extract_dir:
                    logging.info(
                        f"Start extracting downloaded zip file to temporary directory: {temp_extract_dir}"
                    )
                    zip_file.extractall(temp_extract_dir)
                    csv_files = [
                        os.path.join(temp_extract_dir, f)
                        for f in os.listdir(temp_extract_dir)
                        if f.lower().endswith(".csv")
                    ]
                    if csv_files:
                        csv_file_path = ""
                        for csv_file in csv_files:
                            if "avg_losses-mean" in csv_file:
                                csv_file_path = csv_file
                                break
                        save_aal_csv(csv_file_path, openquakejob)
        else:  # in local environment
            # extract to /media/assetupload/filename.zip_extract/
            zip_extract_dir = os.path.join(
                os.path.dirname(aal_csv_zip.file.path),
                "{}_{}".format(os.path.basename(aal_csv_zip.file.path), "extract"),
            )
            with zipfile.ZipFile(aal_csv_zip.file.path, "r") as zip_obj:
                try:
                    if not os.path.isdir(zip_extract_dir):
                        os.mkdir(zip_extract_dir)
                except Exception as err:
                    logging.error(f"ERROR openquake_recapitulate_aal_task: {err}")
                logging.info(
                    f"Start extracting local zip file to directory: {zip_extract_dir}"
                )
                zip_obj.extractall(zip_extract_dir)
                csv_files = [
                    os.path.join(zip_extract_dir, f)
                    for f in os.listdir(zip_extract_dir)
                    if f.lower().endswith(".csv")
                ]
                if csv_files:
                    csv_file_path = ""
                    for csv_file in csv_files:
                        if "avg_losses-mean" in csv_file:
                            csv_file_path = csv_file
                            break
                    save_aal_csv(csv_file_path, openquakejob)
                shutil.rmtree(zip_extract_dir)


@celery_app.task(bind=True, track_started=True, name="openquake_recapitulate_pml_task")
def openquake_recapitulate_pml_task(self, openquakejob_id):
    """
    Import an OpenquakeJob's Aggregate Risk Curves Statistics .csv file rows as OpenquakePMLs.

    Handles .csv uploaded files to local storage or AWS bucket.
    """
    task_id = self.request.id
    task_state = self.AsyncResult(task_id).state
    logging.info(
        f"+++ openquake_recapitulate_pml_task task ID/state: {task_id}/{task_state}"
    )
    openquakejob = OpenquakeJob.objects.get(id=openquakejob_id)
    result_file = openquakejob.result_files.all().filter(
        name="Aggregate Risk Curves Statistics (.csv)"
    )
    if openquakejob.exposure and result_file:
        pml_csv = result_file[0]
        if settings.AWS_STORAGE_BUCKET_NAME:
            file_url = pml_csv.file.url
            logging.info(f"Downloading PML csv file from AWS: {file_url}")
            response = requests.get(file_url, stream=True)
            if response.status_code == requests.codes.ok:
                try:
                    with tempfile.NamedTemporaryFile(
                        suffix=".csv", delete=False
                    ) as temp:
                        for chunk in response.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                temp.write(chunk)
                        temp.flush()
                        temp.seek(0)
                    save_pml_csv(temp.name, openquakejob)
                finally:
                    os.unlink(temp.name)
        else:
            csv_file_path = pml_csv.file.path
            save_pml_csv(csv_file_path, openquakejob)


@celery_app.task(bind=True, track_started=True, name="openquake_submit_calc_task")
def openquake_submit_calc_task(self, openquakejob_id):
    """
    Submit a calculation job to OpenQuake.

    Get a ready OpenQuake calculation server
    Create request session object and authenticate
    POST job archive file to /v1/calc/run
    While job is executing get
    - Job status from /v1/calc/:calc_id/status
    - Job log from /v1/calc/:calc_id/log/[:start]:[:stop]
    On job complete get
    - Job results from /v1/calc/:calc_id/results
    - Job datastore result file from /v1/calc/:calc_id/datastore
    - 202604 also remove completed jobs from OpenQuake.
    """
    task_id = self.request.id
    # !!! task state from celery can be:
    # 'RECEIVED',
    # 'PENDING',
    # 'STARTED',
    # 'RETRY',
    # 'REVOKED',
    # 'FAILURE',
    # 'SUCCESS',
    task_state = self.AsyncResult(task_id).state
    logging.info(
        f"+++ openquake_submit_calc_task task ID/state: {task_id}/{task_state}"
    )
    # get openquakejob instance
    instance = OpenquakeJob.objects.get(id=openquakejob_id)
    instance.task_state = task_state
    instance.task_start = timezone.now()
    # get ready openquake calculation server
    purpose = (
        f"User {instance.user.username if instance.user else 'N/A'} |"
        f" OpenQuake Risk Calculation job ID {instance.id}"
    )
    calculation_server = get_calculation_server(
        type="openquake",
        purpose=purpose,
    )
    if calculation_server and "instance" in calculation_server:
        instance.calculation_server = calculation_server["instance"]
    instance.save()
    if calculation_server:
        logging.info("OpenQuake server is ready!")
        # set calculation server status
        if "instance" in calculation_server:
            calculation_server["instance"].status = "WORKING"
            calculation_server["instance"].save()
        # create job file from exposure data if job archive file is not uploaded
        if instance.exposure and not instance.file:
            openquake_job_archive_file = openquake_generate_job_archive_file(instance)
            if openquake_job_archive_file:
                instance.file = openquake_job_archive_file
                instance.save()
            else:
                error_message = (
                    "FATAL ERROR openquake_submit_calc_task: Failed to generate job archive file for OpenQuake!"
                )
                logging.error(error_message)
                task_state = "FAILURE"
                job_status = "failed"
                self.update_state(state=task_state)
                instance.task_state = task_state
                instance.job_status = job_status
                instance.job_message = error_message
                instance.save()
                if (
                    "instance" in calculation_server
                    and calculation_server["instance"].status == "WORKING"
                ):
                    calculation_server["instance"].status = ""
                    calculation_server["instance"].save()
                # send mail notification to manager and job owner
                send_mail_notification(
                    instance,
                    (
                        f'Failed Risk Calculation job "{instance.name}" (ID: {instance.id} |'
                        f' User: {instance.user.username if instance.user else "N/A"})'
                    ),
                    (
                        f'The Risk Calculation job "{instance.name}"'
                        f' (ID: {instance.id} |'
                        f' User: {instance.user.username if instance.user else "N/A"} |'
                        f' URL: {get_openquakejob_detail_url(instance)})'
                        f' has failed due to => {error_message}',
                    )
                )
                return
        # start new session for requests to openquake
        sess = requests.Session()
        sess = openquake_authenticate(
            sess,
            calculation_server["base_url"],
            calculation_server["user_login"],
            calculation_server["user_password"],
        )
        if not sess:
            error_message = (
                "FATAL ERROR openquake_submit_calc_task: Failed to create authenticated session with OpenQuake!"
            )
            logging.error(error_message)
            task_state = "FAILURE"
            job_status = "failed"
            self.update_state(state=task_state)
            instance.task_state = task_state
            instance.job_status = job_status
            instance.job_message = error_message
            instance.info = error_message
            instance.save()
            if (
                "instance" in calculation_server
                and calculation_server["instance"].status == "WORKING"
            ):
                calculation_server["instance"].status = ""
                calculation_server["instance"].save()
            send_mail_notification(
                instance,
                (
                    f'Failed Risk Calculation job "{instance.name}" (ID: {instance.id} |'
                    f' User: {instance.user.username if instance.user else "N/A"})'
                ),
                (
                    f'The Risk Calculation job "{instance.name}"'
                    f' (ID: {instance.id} |'
                    f' User: {instance.user.username if instance.user else "N/A"} |'
                    f' URL: {get_openquakejob_detail_url(instance)})'
                    f' has failed due to => {error_message}'
                ),
            )
            return
        calc_run_url = urljoin(
            calculation_server["base_url"],
            settings.OPENQUAKE_CALC_RUN_ENDPOINT,
        )
        # submit new calculation with job archive file
        # with open(instance.file.path, "rb") as file:
        file = instance.file.open()  # file may be on s3 bucket
        try:
            logging.info(
                f"OpenQuake POSTing OpenQuake job archive file to: {calc_run_url}"
            )
            resp = sess.post(
                calc_run_url,
                data={},
                files={"archive": file},
            )
            resp.raise_for_status()
        except requests.exceptions.HTTPError as err:
            error_message = (
                f"FATAL ERROR openquake_submit_calc_task: Failed to POST OpenQuake job archive file! ({err})"
            )
            logging.error(error_message)
            task_state = "FAILURE"
            job_status = "failed"
            instance.task_state = task_state
            instance.job_status = job_status
            instance.job_message = error_message
            instance.info = error_message
            instance.save()
            self.update_state(state=task_state)
            if (
                "instance" in calculation_server
                and calculation_server["instance"].status == "WORKING"
            ):
                calculation_server["instance"].status = ""
                calculation_server["instance"].save()
            send_mail_notification(
                instance,
                (
                    f'Failed Risk Calculation job "{instance.name}" (ID: {instance.id} |'
                    f' User: {instance.user.username if instance.user else "N/A"})'
                ),
                (
                    f'The Risk Calculation job "{instance.name}"'
                    f' (ID: {instance.id} |'
                    f' User: {instance.user.username if instance.user else "N/A"} |'
                    f' URL: {get_openquakejob_detail_url(instance)})'
                    f' has failed due to => {error_message}'
                ),
            )
            return
        if "Log in to an existing account" in resp.text:
            error_message = "FATAL ERROR openquake_submit_calc_task: Wrong OpenQuake credentials!"
            logging.error(error_message)
            task_state = "FAILURE"
            job_status = "failed"
            instance.task_state = task_state
            instance.job_status = job_status
            instance.job_message = error_message
            instance.info = error_message
            instance.save()
            self.update_state(state=task_state)
            if (
                "instance" in calculation_server
                and calculation_server["instance"].status == "WORKING"
            ):
                calculation_server["instance"].status = ""
                calculation_server["instance"].save()
            send_mail_notification(
                instance,
                (
                    f'Failed Risk Calculation job "{instance.name}" (ID: {instance.id} |'
                    f' User: {instance.user.username if instance.user else "N/A"})'
                ),
                (
                    f'The Risk Calculation job "{instance.name}"'
                    f' (ID: {instance.id} |'
                    f' User: {instance.user.username if instance.user else "N/A"} |'
                    f' URL: {get_openquakejob_detail_url(instance)})'
                    f' has failed due to => {error_message}'
                ),
            )
            return
        elif resp.status_code == requests.codes.ok:
            # get new job details
            job = json.loads(resp.text)
            # !!! job status from openquake can be:
            # 'created',
            # 'submitted',
            # 'executing',
            # 'complete',
            # 'aborted',
            # 'failed',
            # 'deleted'
            job_status = job["status"]
            if job_status == "created":
                job_id = job["job_id"]
                instance.job_id = job_id
                instance.job_status = job_status
                # save initial job status
                instance.save()
                counter = 0
                job_status_errors = 0
                exposure_count = instance.exposure.assets.count() if instance.exposure else 0
                send_mail_notification(
                    instance,
                    (
                        f'Executing Risk Calculation job "{instance.name}" (ID: {instance.id} |'
                        f' User: {instance.user.username if instance.user else "N/A"} |'
                        f' OpenQuake Job ID: {instance.job_id}) |'
                        f' Exposure Count: {exposure_count}'
                    ),
                    (
                        f'The Risk Calculation job "{instance.name}"'
                        f' (ID: {instance.id} |'
                        f' User: {instance.user.username if instance.user else "N/A"} |'
                        f' OpenQuake Job ID: {instance.job_id} |'
                        f' Exposure Count: {exposure_count} |'
                        f' URL: {get_openquakejob_detail_url(instance)}) has started executing!'
                    )
                )
                # stop job on SoftTimeLimitExceeded before the celery task is killed on TimeLimitExceeded
                try:
                    # poll for job status every 1s until it is complete
                    while job_status != "complete":
                        status = openquake_get_job_status(
                            sess,
                            calculation_server["base_url"],
                            job_id,
                        )
                        if not status:
                            job_status_errors += 1
                            # quit if threshold job status errors exceeded
                            if (
                                job_status_errors
                                == settings.OPENQUAKE_JOB_STATUS_MAX_ERRORS
                            ):
                                error_message = (
                                    f"FATAL ERROR openquake_submit_calc_task: "
                                    f"Too many failures to get job {instance.job_id} status!"
                                )
                                logging.error(error_message)
                                task_state = "FAILURE"
                                instance.task_state = task_state
                                instance.job_status = "failed"
                                instance.info = error_message
                                # 202607 get job traceback on error
                                job_traceback = openquake_get_job_traceback(
                                    sess, calculation_server["base_url"], job_id
                                )
                                instance.job_message = json.dumps(
                                    job_traceback, indent=4
                                )
                                instance.save()
                                self.update_state(state=task_state)
                                if "instance" in calculation_server:
                                    calculation_server["instance"].status = ""
                                    calculation_server["instance"].save()
                                send_mail_notification(
                                    instance,
                                    (
                                        f'Failed Risk Calculation job "{instance.name}" (ID: {instance.id} |'
                                        f' User: {instance.user.username if instance.user else "N/A"} |'
                                        f' OpenQuake Job ID: {instance.job_id})'
                                    ),
                                    (
                                        f'The Risk Calculation job "{instance.name}"'
                                        f' (ID: {instance.id} |'
                                        f' User: {instance.user.username if instance.user else "N/A"} |'
                                        f' OpenQuake Job ID: {instance.job_id} |'
                                        f' URL: {get_openquakejob_detail_url(instance)}'
                                        f' has failed due to => {error_message}'
                                    ),
                                )
                                # 202604
                                openquake_remove_calc_task.delay(
                                    openquakejob_id=instance.id
                                )
                                return
                        job_status = status["status"]
                        instance.job_status = job_status
                        logging.info(f"Job {job_id} status: {job_status} ({counter})")
                        # get job log every interval
                        if counter % settings.OPENQUAKE_JOB_STATUS_INTERVAL == 0:
                            job_log = openquake_get_job_log(
                                sess,
                                calculation_server["base_url"],
                                job_id,
                            )
                            if job_log and job_status != "complete":
                                # save prettified json job log
                                instance.job_message = json.dumps(job_log, indent=4)
                                instance.save()
                        # quit if on openquake the job failed/aborted/deleted
                        if (
                            job_status == "failed"
                            or job_status == "aborted"
                            or job_status == "deleted"
                        ):
                            error_message = f"FATAL ERROR openquake_submit_calc_task: job {job_id} {job_status}!"
                            logging.error(error_message)
                            task_state = "FAILURE"
                            instance.task_state = task_state
                            instance.info = error_message
                            # 202607 get job traceback on error
                            job_traceback = openquake_get_job_traceback(
                                sess, calculation_server["base_url"], job_id
                            )
                            instance.job_message = json.dumps(job_traceback, indent=4)
                            instance.save()
                            self.update_state(state=task_state)
                            if "instance" in calculation_server:
                                calculation_server["instance"].status = ""
                                calculation_server["instance"].save()
                            send_mail_notification(
                                instance,
                                (
                                    f'Failed Risk Calculation job "{instance.name}" (ID: {instance.id} |'
                                    f' User: {instance.user.username if instance.user else "N/A"} |'
                                    f' OpenQuake Job ID: {instance.job_id})'
                                ),
                                (
                                    f'The Risk Calculation job "{instance.name}"'
                                    f' (ID: {instance.id} |'
                                    f' User: {instance.user.username if instance.user else "N/A"} |'
                                    f' OpenQuake Job ID: {instance.job_id} |'
                                    f' URL: {get_openquakejob_detail_url(instance)})'
                                    f' has failed due to => {error_message}'
                                ),
                            )
                            # 202604
                            openquake_remove_calc_task.delay(
                                openquakejob_id=instance.id
                            )
                            return
                        time.sleep(1)
                        counter += 1
                except SoftTimeLimitExceeded:
                    # abort the job on openquake
                    openquake_abort_job(sess, calculation_server["base_url"], job_id)
                    time_limit_minutes = airisiko_seconds_to_minutes(
                        settings.CELERY_TASK_SOFT_TIME_LIMIT
                    )
                    error_message = (
                        f"FATAL ERROR openquake_submit_calc_task: job {job_id} aborted due to exceeding time limit of"
                        f" {time_limit_minutes} minutes!"
                    )
                    logging.error(error_message)
                    task_state = "FAILURE"
                    job_status = "failed"
                    instance.task_state = task_state
                    instance.job_status = job_status
                    instance.info = error_message
                    # 202607 get job traceback on error
                    job_traceback = openquake_get_job_traceback(
                        sess, calculation_server["base_url"], job_id
                    )
                    instance.job_message = json.dumps(job_traceback, indent=4)
                    instance.save()
                    if "instance" in calculation_server:
                        calculation_server["instance"].status = ""
                        calculation_server["instance"].save()
                    send_mail_notification(
                        instance,
                        (
                            f'Failed Risk Calculation job "{instance.name}" (ID: {instance.id} |'
                            f' User: {instance.user.username if instance.user else "N/A"} |'
                            f' OpenQuake Job ID: {instance.job_id})'
                        ),
                        (
                            f'The Risk Calculation job "{instance.name}"'
                            f' (ID: {instance.id} |'
                            f' User: {instance.user.username if instance.user else "N/A"} |'
                            f' OpenQuake Job ID: {instance.job_id} |'
                            f' URL: {get_openquakejob_detail_url(instance)})'
                            f' has failed due to => {error_message}'
                        ),
                    )
                    # 202604
                    openquake_remove_calc_task.delay(openquakejob_id=instance.id)
                    return
                logging.info(f"Job {job_id} complete!")
                # get job results and download datastore result file
                if instance.job_status == "complete":
                    job_results = openquake_get_job_results(
                        sess,
                        calculation_server["base_url"],
                        job_id,
                    )
                    if job_results:
                        # save prettified json job results
                        instance.job_results = json.dumps(job_results, indent=4)
                        openquake_get_job_results_files(
                            sess,
                            calculation_server["base_url"],
                            job_results,
                            job_id,
                            instance,
                        )
                        openquake_get_job_datastore_file(
                            sess,
                            calculation_server["base_url"],
                            job_id,
                            instance,
                        )
                        # recapitulate PML asynchronously
                        openquake_recapitulate_pml_task.delay(
                            openquakejob_id=instance.id
                        )
                        # recapitulate AAL asynchronously
                        openquake_recapitulate_aal_task.delay(
                            openquakejob_id=instance.id
                        )
                    # task successful here
                    task_state = "SUCCESS"
                    instance.task_end = timezone.now()
                    instance.task_state = task_state
                    instance.save()
                    self.update_state(state=task_state)
                    if (
                        "instance" in calculation_server
                        and calculation_server["instance"].status == "WORKING"
                    ):
                        calculation_server["instance"].status = ""
                        calculation_server["instance"].save()
                    send_mail_notification(
                        instance,
                        (
                            f'Completed Risk Calculation job "{instance.name}" (ID: {instance.id} |'
                            f' User: {instance.user.username if instance.user else "N/A"} |'
                            f' OpenQuake Job ID: {instance.job_id})'
                        ),
                        (
                            f'The Risk Calculation job "{instance.name}"'
                            f' (ID: {instance.id} |'
                            f' User: {instance.user.username if instance.user else "N/A"} |'
                            f' OpenQuake Job ID: {instance.job_id} |'
                            f' URL: {get_openquakejob_detail_url(instance)})'
                            f' has completed successfully!'
                        ),
                    )
                    openquake_remove_calc_task.delay(openquakejob_id=instance.id)
            else:
                error_message = "FATAL ERROR openquake_submit_calc_task: Failed to create OpenQuake job!"
                logging.error(error_message)
                task_state = "FAILURE"
                job_status = "failed"
                instance.task_state = task_state
                instance.job_status = job_status
                instance.job_message = error_message
                instance.info = error_message
                instance.save()
                self.update_state(state=task_state)
                if (
                    "instance" in calculation_server
                    and calculation_server["instance"].status == "WORKING"
                ):
                    calculation_server["instance"].status = ""
                    calculation_server["instance"].save()
                send_mail_notification(
                    instance,
                    (
                        f'Failed Risk Calculation job "{instance.name}" (ID: {instance.id} |'
                        f' User: {instance.user.username if instance.user else "N/A"})'
                    ),
                    (
                        f'The Risk Calculation job "{instance.name}"'
                        f' (ID: {instance.id} |'
                        f' User: {instance.user.username if instance.user else "N/A"} |'
                        f' URL: {get_openquakejob_detail_url(instance)})'
                        f' has failed due to => {error_message}'
                    ),
                )
                return
        else:
            error_message = f"FATAL ERROR openquake_submit_calc_task: {resp.text}"
            logging.error(error_message)
            task_state = "FAILURE"
            job_status = "failed"
            instance.task_state = task_state
            instance.job_status = job_status
            instance.job_message = error_message
            instance.info = error_message
            instance.save()
            self.update_state(state=task_state)
            if "instance" in calculation_server:
                calculation_server["instance"].status = ""
                calculation_server["instance"].save()
            send_mail_notification(
                instance,
                (
                    f'Failed Risk Calculation job "{instance.name}" (ID: {instance.id} |'
                    f' User: {instance.user.username if instance.user else "N/A"})'
                ),
                (
                    f'The Risk Calculation job "{instance.name}"'
                    f' (ID: {instance.id} |'
                    f' User: {instance.user.username if instance.user else "N/A"} |'
                    f' URL: {get_openquakejob_detail_url(instance)})'
                    f' has failed due to => {error_message}'
                ),
            )
            return
    else:
        error_message = "FATAL ERROR openquake_submit_calc_task: No OpenQuake server found!"
        logging.error(error_message)
        task_state = "FAILURE"
        job_status = "failed"
        instance.task_state = task_state
        instance.job_status = job_status
        instance.job_message = error_message
        instance.info = error_message
        instance.save()
        self.update_state(state=task_state)
        send_mail_notification(
            instance,
            (
                f'Failed Risk Calculation job "{instance.name}" (ID: {instance.id} |'
                f' User: {instance.user.username if instance.user else "N/A"})'
            ),
            (
                f'The Risk Calculation job "{instance.name}"'
                f' (ID: {instance.id} |'
                f' User: {instance.user.username if instance.user else "N/A"} |'
                f' URL: {get_openquakejob_detail_url(instance)})'
                f' has failed due to => {error_message}'
            ),
        )
        return


@celery_app.task(bind=True, track_started=True, name="openquake_abort_calc_task")
def openquake_abort_calc_task(self, openquakejob_id, delete=False):
    """
    Send an abort request for a running OpenQuake calculation job.

    Stop openquake_submit_calc_task first then send abort calc request to
    /v1/calc/:calc_id/abort.
    """
    task_id = self.request.id
    task_state = self.AsyncResult(task_id).state
    logging.info(f"+++ openquake_abort_calc_task task ID/state: {task_id}/{task_state}")
    instance = OpenquakeJob.objects.get(id=openquakejob_id)
    # stop celery task
    if instance.task_id:
        celery_app.control.revoke(instance.task_id, terminate=True, signal="SIGKILL")
        logging.info(f"Task {instance.task_id} revoked!")
    base_url = settings.OPENQUAKE_BASE_URL
    user_login = settings.OPENQUAKE_ADMIN_LOGIN
    user_password = settings.OPENQUAKE_ADMIN_PASSWORD
    job_id = instance.job_id
    if instance.calculation_server:
        base_url = instance.calculation_server.base_url
        user_login = instance.calculation_server.user_login
        user_password = instance.calculation_server.user_password
    sess = requests.Session()
    sess = openquake_authenticate(sess, base_url, user_login, user_password)
    if not sess:
        return
    job_aborted = openquake_abort_job(sess, base_url, job_id)
    if job_aborted:
        instance.job_status = "aborted"
        instance.save()
        if (
            instance.calculation_server
            and instance.calculation_server.status == "WORKING"
        ):
            instance.calculation_server.status = ""
            instance.calculation_server.save()
        send_mail_notification(
            instance,
            (
                f'[BACKEND TASK] Aborted Risk Calculation job "{instance.name}" (ID: {instance.id} |'
                f' User: {instance.user.username if instance.user else "N/A"} |'
                f' OpenQuake Job ID: {instance.job_id})'
            ),
            (
                f'The Risk Calculation job "{instance.name}"'
                f' (ID: {instance.id} |'
                f' User: {instance.user.username if instance.user else "N/A"} |'
                f' OpenQuake Job ID: {instance.job_id} |'
                f' URL: {get_openquakejob_detail_url(instance)})'
                f' has been aborted!'
            ),
            True,
        )
        if delete:
            instance.delete()


@celery_app.task(bind=True, track_started=True, name="openquake_remove_calc_task")
def openquake_remove_calc_task(self, openquakejob_id):
    """
    Send an remove request for an OpenQuake calculation job.

    The OpenQuake job status must be complete, aborted, or failed before sending
    remove request to /v1/calc/:calc_id/remove.
    """
    task_id = self.request.id
    task_state = self.AsyncResult(task_id).state
    logging.info(
        f"+++ openquake_remove_calc_task task ID/state: {task_id}/{task_state}"
    )
    instance = OpenquakeJob.objects.get(id=openquakejob_id)
    if (
        instance.job_status == "complete"
        or instance.job_status == "aborted"
        or instance.job_status == "failed"
    ):
        base_url = settings.OPENQUAKE_BASE_URL
        user_login = settings.OPENQUAKE_ADMIN_LOGIN
        user_password = settings.OPENQUAKE_ADMIN_PASSWORD
        job_id = instance.job_id
        if instance.calculation_server:
            base_url = instance.calculation_server.base_url
            user_login = instance.calculation_server.user_login
            user_password = instance.calculation_server.user_password
        sess = requests.Session()
        sess = openquake_authenticate(sess, base_url, user_login, user_password)
        if not sess:
            return
        job_removed = openquake_remove_job(sess, base_url, job_id)
        if job_removed:
            send_mail_notification(
                instance,
                (
                    f'[BACKEND TASK] Removed Risk Calculation job "{instance.name}" (ID: {instance.id} |'
                    f' User: {instance.user.username if instance.user else "N/A"} |'
                    f' OpenQuake Job ID: {instance.job_id})'
                ),
                f'The Risk Calculation job "{instance.name}"'
                f' (ID: {instance.id} |'
                f' User: {instance.user.username if instance.user else "N/A"} |'
                f' OpenQuake Job ID: {instance.job_id} |'
                f' URL: {get_openquakejob_detail_url(instance)})'
                f' has been removed!',
                True,
            )


@celery_app.task(
    bind=True, track_started=True, name="openquake_check_complete_calc_task"
)
def openquake_check_complete_calc_task(self):
    """
    Check created/executing jobs in case the openquake_submit_calc_task was killed.

    If the OpenQuake job status on the calculation server is complete then update
    the local job status and retrieve results.

    202604 also remove completed jobs from OpenQuake.
    """
    task_id = self.request.id
    task_state = self.AsyncResult(task_id).state
    logging.info(
        f"+++ openquake_check_complete_calc_task task ID/state: {task_id}/{task_state}"
    )
    openquakejobs = OpenquakeJob.objects.filter(
        Q(job_status="created") | Q(job_status="executing")
    )
    for openquakejob in openquakejobs:
        openquakejob_id = openquakejob.id
        logging.info(
            f"openquake_check_complete_calc_task: Checking complete calculation for openquakejob {openquakejob}"
        )
        task_state = self.AsyncResult(openquakejob.task_id).state
        # try to check job status in calculation server
        base_url = settings.OPENQUAKE_BASE_URL
        user_login = settings.OPENQUAKE_ADMIN_LOGIN
        user_password = settings.OPENQUAKE_ADMIN_PASSWORD
        job_id = openquakejob.job_id
        if openquakejob.calculation_server:
            base_url = openquakejob.calculation_server.base_url
            user_login = openquakejob.calculation_server.user_login
            user_password = openquakejob.calculation_server.user_password
        sess = requests.Session()
        sess = openquake_authenticate(sess, base_url, user_login, user_password)
        if not sess:
            return
        job_status = openquake_get_job_status(sess, base_url, job_id)
        if not job_status:
            # check for latest queryset in case record has been deleted in admin
            # if not checked first then cached queryset will recreate record!
            try:
                openquakejob = OpenquakeJob.objects.get(id=openquakejob_id)
                warning_message = f"WARNING: Failed to get job status for job {job_id}, marking job as failed!"
                logging.warning(warning_message)
                openquakejob.job_status = "failed"
                openquakejob.task_state = "FAILURE"
                openquakejob.info = warning_message
                if (
                    openquakejob.calculation_server
                    and openquakejob.calculation_server.status == "WORKING"
                ):
                    openquakejob.calculation_server.status = ""
                    openquakejob.calculation_server.save()
                openquakejob.save()
            except ObjectDoesNotExist:
                logging.warning(f"OpenquakeJob ID {openquakejob_id} was deleted!")
                break
            return
        task_state = self.AsyncResult(openquakejob.task_id).state
        # only download results if task has failed!
        if job_status["status"] == "complete" and task_state == "FAILURE":
            try:
                openquakejob = OpenquakeJob.objects.get(id=openquakejob_id)
                job_results = openquake_get_job_results(sess, base_url, job_id)
                if job_results:
                    # get all calculation result files
                    openquakejob.job_results = json.dumps(job_results, indent=4)
                    openquake_get_job_results_files(
                        sess, base_url, job_results, job_id, openquakejob
                    )
                    openquake_get_job_datastore_file(
                        sess, base_url, job_id, openquakejob
                    )
                    # recapitulate PML asynchronously
                    openquake_recapitulate_pml_task.delay(
                        openquakejob_id=openquakejob.id
                    )
                    # recapitulate AAL asynchronously
                    openquake_recapitulate_aal_task.delay(
                        openquakejob_id=openquakejob.id
                    )
                openquakejob.job_status = "complete"
                openquakejob.task_state = "SUCCESS"
                openquakejob.task_end = timezone.now()
                openquakejob.save()
                if (
                    openquakejob.calculation_server
                    and openquakejob.calculation_server.status == "WORKING"
                ):
                    openquakejob.calculation_server.status = ""
                    openquakejob.calculation_server.save()
                send_mail_notification(
                    openquakejob,
                    (
                        f'[BACKEND TASK] Checked completed Risk Calculation job "{openquakejob.name}"'
                        f' (ID: {openquakejob.id} |'
                        f' User: {openquakejob.user.username if openquakejob.user else "N/A"} |'
                        f' OpenQuake Job ID: {openquakejob.job_id})'
                    ),
                    (
                        f'The Risk Calculation job "{openquakejob.name}"'
                        f' (ID: {openquakejob.id} |'
                        f' User: {openquakejob.user.username if openquakejob.user else "N/A"} |'
                        f' OpenQuake Job ID: {openquakejob.job_id} |'
                        f' URL: {get_openquakejob_detail_url(openquakejob)})'
                        f' has completed successfully!'
                    ),
                    True,
                )
                # 202604
                openquake_remove_calc_task.delay(openquakejob_id=openquakejob.id)
            except ObjectDoesNotExist:
                logging.warning(f"OpenquakeJob ID {openquakejob_id} was deleted!")
                break


@celery_app.task(
    bind=True, track_started=True, name="calculation_server_check_active_task"
)
def calculation_server_check_active_task(self):
    """
    Check enabled calculation servers if they are active.
    """
    # 202607 override settings.REQUESTS_CONNECTION_TIMEOUT REQUESTS_MAX_CONNECTION_TRIES REQUESTS_SLEEP_TIME
    # to avoid long task wait when a calc server is offline
    requests_connection_timeout = settings.REQUESTS_CONNECTION_TIMEOUT
    requests_max_connection_tries = settings.REQUESTS_MAX_CONNECTION_TRIES
    requests_sleep_time = settings.REQUESTS_SLEEP_TIME
    requests_connection_timeout = 2
    requests_max_connection_tries = 1
    requests_sleep_time = 0
    task_id = self.request.id
    task_state = self.AsyncResult(task_id).state
    logging.info(
        f"+++ calculation_server_check_active_task task ID/state: {task_id}/{task_state}"
    )
    calculationservers = CalculationServer.objects.filter(enabled=True)
    for calculationserver in calculationservers:
        calculationserver_id = calculationserver.id
        logging.info(
            f"calculation_server_check_active_task: Checking calculation server for {calculationserver}"
        )
        page = ""
        tries = 0
        # try waiting until remote server is ready...
        while page == "":
            try:
                tries += 1
                logging.info(
                    f"Server connection to {calculationserver} try number: {tries}"
                )
                try:
                    # check for latest queryset in case record has been deleted in admin
                    # if not checked first then cached queryset will recreate record!
                    calculationserver = CalculationServer.objects.get(
                        id=calculationserver_id
                    )
                    calculationserver.last_checked = timezone.now()
                    calculationserver.save()
                except ObjectDoesNotExist:
                    logging.warning(
                        f"Calculation server ID {calculationserver_id} was deleted!"
                    )
                    break
                page = requests.get(
                    calculationserver.base_url,
                    timeout=requests_connection_timeout,
                )
                page.raise_for_status()
                break
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.HTTPError,  # handle HTTPError 502 bad gateway
            ) as err:
                # reset page since HTTPError 502 will set page as Response [502]
                page = ""
                # mark server as inactive if max connection tries reached
                if tries == requests_max_connection_tries:
                    logging.info(
                        f"Max connection tries reached. Marking server {calculationserver} as inactive!"
                    )
                    try:
                        calculationserver = CalculationServer.objects.get(
                            id=calculationserver_id
                        )
                        calculationserver.active = False
                        # also reset status in case if stuck on WORKING
                        if calculationserver.status == "WORKING":
                            calculationserver.status = ""
                        calculationserver.save()
                    except ObjectDoesNotExist:
                        logging.warning(
                            f"Calculation server ID {calculationserver_id} was deleted!"
                        )
                        break
                    break
                logging.warning(err)
                logging.info(f"Connection refused by the server {calculationserver}...")
                logging.info(f"Sleeping for {requests_sleep_time} seconds...")
                logging.info("Zzz...")
                time.sleep(requests_sleep_time)
                logging.info("Now try again...")
                continue
        if page:
            # server is active!
            logging.info(
                f"Server {calculationserver} responded. Marking server as active!"
            )
            calculationserver.last_active = timezone.now()
            calculationserver.active = True
            calculationserver.save()


@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    """
    Define periodic celery tasks.
    """
    sender.add_periodic_task(
        60,
        calculation_server_check_active_task.s(),
        name="calculation_server_check_active_task",
    )
    sender.add_periodic_task(
        60,
        openquake_check_complete_calc_task.s(),
        name="openquake_check_complete_calc_task",
    )
