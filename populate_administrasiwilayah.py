import datetime
import os

import django
import psycopg2
from django.core.exceptions import ObjectDoesNotExist

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from ai_risiko.administrasiwilayah.models import (  # noqa: E402
    Desa,
    Kabupaten_Kota,
    Kecamatan,
    Provinsi,
    Pulau,
)

connection_string = (
    "host='postgres'"
    " dbname='peponline'"
    " user ='buCvSEmfSDUtugnUxRrCWsEVAsQmBdJg'"
    " password='bSRlFb37yvDPoCGEOp57RUa1XMTe29tWk08n8L3b6Fp9JXGE6OuzpnCXuOdoXRbN'"
)

if __name__ == "__main__":
    conn = psycopg2.connect(connection_string)

    COUNT_PULAU = 0
    COUNT_PULAU_CREATE = 0
    COUNT_PULAU_UPDATE = 0
    COUNT_PROVINSI = 0
    COUNT_PROVINSI_CREATE = 0
    COUNT_PROVINSI_UPDATE = 0
    COUNT_KABUPATEN_KOTA = 0
    COUNT_KABUPATEN_KOTA_CREATE = 0
    COUNT_KABUPATEN_KOTA_UPDATE = 0
    COUNT_KECAMATAN = 0
    COUNT_KECAMATAN_CREATE = 0
    COUNT_KECAMATAN_UPDATE = 0
    COUNT_DESA = 0
    COUNT_DESA_CREATE = 0
    COUNT_DESA_UPDATE = 0

    TIME_START = str(datetime.datetime.now())

    # import Pulau
    cur = conn.cursor()
    sql_pulau = "SELECT * FROM tingkatanwilayah_pulau"
    cur.execute(sql_pulau)
    rows_pulau = cur.fetchall()
    list_pulau = [
        Pulau(
            id=row_pulau[0], nama=row_pulau[1], polygon=row_pulau[2], luas=row_pulau[5]
        )
        for row_pulau in rows_pulau
    ]

    for pulau in list_pulau:
        COUNT_PULAU += 1

        if not pulau.nama:
            pulau.nama = ""
        try:
            pulau_instance = Pulau.objects.get(id=pulau.id)
            pulau_instance.nama = pulau.nama
            pulau_instance.polygon = pulau.polygon
            pulau_instance.luas = pulau.luas
            print(f"Updating Pulau: {pulau_instance.id} {pulau_instance.nama}")
            pulau_instance.save()
            COUNT_PULAU_UPDATE += 1
        except ObjectDoesNotExist:
            print(f"Pulau DNE, creating new: {pulau.nama}")
            pulau_instance = pulau
            pulau_instance.save()
            COUNT_PULAU_CREATE += 1

        # import Provinsi
        cur2 = conn.cursor()
        sql_provinsi = (
            "SELECT * FROM tingkatanwilayah_provinsi WHERE pulau_id = {}".format(
                pulau_instance.id
            )
        )
        cur2.execute(sql_provinsi)
        rows_provinsi = cur2.fetchall()
        list_provinsi = [
            Provinsi(
                id=row_provinsi[0],
                nama=row_provinsi[1],
                polygon=row_provinsi[2],
                luas=row_provinsi[6],
                pulau=pulau_instance,
            )
            for row_provinsi in rows_provinsi
        ]

        for provinsi in list_provinsi:
            COUNT_PROVINSI += 1

            if not provinsi.nama:
                provinsi.nama = ""
            try:
                provinsi_instance = Provinsi.objects.get(id=provinsi.id)
                provinsi_instance.nama = provinsi.nama
                provinsi_instance.polygon = provinsi.polygon
                provinsi_instance.luas = provinsi.luas
                provinsi_instance.pulau = provinsi.pulau
                print(
                    "Updating Provinsi: {} {}".format(
                        provinsi_instance.id, provinsi_instance.nama
                    )
                )
                provinsi_instance.save()
                COUNT_PROVINSI_UPDATE += 1
            except ObjectDoesNotExist:
                print(f"Provinsi DNE, creating new: {provinsi.nama}")
                provinsi_instance = provinsi
                provinsi_instance.save()
                COUNT_PROVINSI_CREATE += 1

            # import Kabupaten_Kota
            cur3 = conn.cursor()
            sql_kabupaten_kota = "SELECT * FROM tingkatanwilayah_kabupaten_kota WHERE provinsi_id = {}".format(
                provinsi_instance.id
            )
            cur3.execute(sql_kabupaten_kota)
            rows_kabupaten_kota = cur3.fetchall()
            list_kabupaten_kota = [
                Kabupaten_Kota(
                    id=row_kabupaten_kota[0],
                    nama=row_kabupaten_kota[1],
                    polygon=row_kabupaten_kota[2],
                    luas=row_kabupaten_kota[6],
                    id_kemendagri=row_kabupaten_kota[7],
                    nama_kemendagri=row_kabupaten_kota[8],
                    provinsi=provinsi_instance,
                )
                for row_kabupaten_kota in rows_kabupaten_kota
            ]

            for kabupaten_kota in list_kabupaten_kota:
                COUNT_KABUPATEN_KOTA += 1

                if not kabupaten_kota.nama:
                    kabupaten_kota.nama = ""
                try:
                    kabupaten_kota_instance = Kabupaten_Kota.objects.get(
                        id=kabupaten_kota.id
                    )
                    kabupaten_kota_instance.nama = kabupaten_kota.nama
                    kabupaten_kota_instance.polygon = kabupaten_kota.polygon
                    kabupaten_kota_instance.luas = kabupaten_kota.luas
                    kabupaten_kota_instance.id_kemendagri = kabupaten_kota.id_kemendagri
                    kabupaten_kota_instance.nama_kemendagri = (
                        kabupaten_kota.nama_kemendagri
                    )
                    kabupaten_kota_instance.provinsi = kabupaten_kota.provinsi
                    print(
                        "Updating Kabupaten_Kota: {} {}".format(
                            kabupaten_kota_instance.id, kabupaten_kota_instance.nama
                        )
                    )
                    kabupaten_kota_instance.save()
                    COUNT_KABUPATEN_KOTA_UPDATE += 1
                except ObjectDoesNotExist:
                    print(
                        "Kabupaten_Kota DNE, creating new: {}".format(
                            kabupaten_kota.nama
                        )
                    )
                    kabupaten_kota_instance = kabupaten_kota
                    kabupaten_kota_instance.save()
                    COUNT_KABUPATEN_KOTA_CREATE += 1

                # import Kecamatan
                cur4 = conn.cursor()
                sql_kecamatan = "SELECT * FROM tingkatanwilayah_kecamatan WHERE kabupaten_kota_id = {}".format(
                    kabupaten_kota_instance.id
                )
                cur4.execute(sql_kecamatan)
                rows_kecamatan = cur4.fetchall()
                list_kecamatan = [
                    Kecamatan(
                        id=row_kecamatan[0],
                        nama=row_kecamatan[1],
                        polygon=row_kecamatan[2],
                        luas=row_kecamatan[6],
                        id_kemendagri=row_kecamatan[7],
                        nama_kemendagri=row_kecamatan[8],
                        kabupaten_kota=kabupaten_kota_instance,
                    )
                    for row_kecamatan in rows_kecamatan
                ]

                for kecamatan in list_kecamatan:
                    COUNT_KECAMATAN += 1

                    if not kecamatan.nama:
                        kecamatan.nama = ""
                    try:
                        kecamatan_instance = Kecamatan.objects.get(id=kecamatan.id)
                        kecamatan_instance.polygon = kecamatan.polygon
                        kecamatan_instance.luas = kecamatan.luas
                        kecamatan_instance.id_kemendagri = kecamatan.id_kemendagri
                        kecamatan_instance.nama_kemendagri = kecamatan.nama_kemendagri
                        kecamatan_instance.kabupaten_kota = kecamatan.kabupaten_kota
                        print(
                            "Updating Kecamatan: {} {}".format(
                                kecamatan_instance.id, kecamatan_instance.nama
                            )
                        )
                        kecamatan_instance.save()
                        COUNT_KECAMATAN_UPDATE += 1
                    except ObjectDoesNotExist:
                        print(f"Kecamatan DNE, creating new: {kecamatan.nama}")
                        kecamatan_instance = kecamatan
                        kecamatan_instance.save()
                        COUNT_KECAMATAN_CREATE += 1

                    # import Desa
                    cur5 = conn.cursor()
                    sql_desa = "SELECT * FROM tingkatanwilayah_desa WHERE kecamatan_id = {}".format(
                        kecamatan_instance.id
                    )
                    cur5.execute(sql_desa)
                    rows_desa = cur5.fetchall()
                    list_desa = [
                        Desa(
                            id=row_desa[0],
                            nama=row_desa[1],
                            polygon=row_desa[2],
                            luas=row_desa[6],
                            id_kemendagri=row_desa[7],
                            nama_kemendagri=row_desa[8],
                            kecamatan=kecamatan_instance,
                        )
                        for row_desa in rows_desa
                    ]

                    for desa in list_desa:
                        COUNT_DESA += 1

                        if not desa.nama:
                            desa.nama = ""
                        try:
                            desa_instance = Desa.objects.get(id=desa.id)
                            desa_instance.nama = desa.nama
                            desa_instance.polygon = desa.polygon
                            desa_instance.luas = desa.luas
                            desa_instance.id_kemendagri = desa.id_kemendagri
                            desa_instance.nama_kemendagri = desa.nama_kemendagri
                            desa_instance.kecamatan = desa.kecamatan
                            print(
                                "updating Desa: {} {}".format(
                                    desa_instance.id, desa_instance.nama
                                )
                            )
                            desa_instance.save()
                            COUNT_DESA_UPDATE += 1
                        except ObjectDoesNotExist:
                            print(f"Desa DNE, creating new: {desa.nama}")
                            desa_instance = desa
                            desa_instance.save()
                            COUNT_DESA_CREATE += 1

    TIME_FINISH = str(datetime.datetime.now())

    print("SUMMARY")
    print("")
    print("=" * 80)
    print("")
    print("SUMMARY")
    print("")
    print(f"START\t: {TIME_START}")
    print(f"FINISH\t: {TIME_FINISH}")
    print("")
    print(f"Pulau Total\t\t\t\t: {COUNT_PULAU}")
    print(f"Pulau Created\t\t\t\t: {COUNT_PULAU_CREATE}")
    print(f"Pulau Updated\t\t\t\t: {COUNT_PULAU_UPDATE}")
    print(f"Provinsi Total\t\t\t\t: {COUNT_PROVINSI}")
    print(f"Provinsi Created\t\t\t: {COUNT_PROVINSI_CREATE}")
    print(f"Provinsi Updated\t\t\t: {COUNT_PROVINSI_UPDATE}")
    print(f"Kabupaten_Kota Total\t\t: {COUNT_KABUPATEN_KOTA}")
    print(f"Kabupaten_Kota Created\t\t: {COUNT_KABUPATEN_KOTA_CREATE}")
    print(f"Kabupaten_Kota Updated\t\t: {COUNT_KABUPATEN_KOTA_UPDATE}")
    print(f"Kecamatan Total\t\t\t\t: {COUNT_KECAMATAN}")
    print(f"Kecamatan Created\t\t\t: {COUNT_KECAMATAN_CREATE}")
    print(f"Kecamatan Updated\t\t\t: {COUNT_KECAMATAN_UPDATE}")
    print(f"Desa Total\t\t\t\t\t: {COUNT_DESA}")
    print(f"Desa Created\t\t\t\t: {COUNT_DESA_CREATE}")
    print(f"Desa Updated\t\t\t\t: {COUNT_DESA_UPDATE}")
