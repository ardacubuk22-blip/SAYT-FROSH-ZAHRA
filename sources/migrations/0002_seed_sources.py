from datetime import timedelta

from django.db import migrations

SOURCES = [
    # (adapter, name, url, type, access_method, is_active, notes)
    ("kultursanat", "Kültür Sanat İstanbul (İBB)", "https://kultursanat.istanbul/", "events", "crawler", True,
     "اولویت اول. ساختار لینک‌ها و قوانین سایت باید بعد از باز شدن دسترسی شبکه بررسی شود."),
    ("ibb_ckan", "İBB Açık Veri (CKAN)", "https://data.ibb.gov.tr/", "venues", "open_data", False,
     "API از نوع CKAN برای فهرست مکان‌ها — مرحله‌ی ۳."),
    ("akm", "Atatürk Kültür Merkezi (AKM)", "https://www.akmistanbul.gov.tr/", "events", "crawler", False, "مرحله‌ی ۳."),
    ("sehir_tiyatrolari", "İBB Şehir Tiyatroları", "https://sehirtiyatrolari.ibb.istanbul/", "events", "crawler",
     False, "مرحله‌ی ۳."),
    ("iksv", "İKSV", "https://www.iksv.org/", "events", "crawler", False, "مرحله‌ی ۳."),
]


def seed(apps, schema_editor):
    City = apps.get_model("core", "City")
    Source = apps.get_model("sources", "Source")
    City.objects.get_or_create(slug="istanbul", defaults={"name": "İstanbul", "name_fa": "استانبول"})
    for adapter, name, url, type_, method, active, notes in SOURCES:
        Source.objects.get_or_create(
            adapter=adapter,
            defaults=dict(name=name, url=url, type=type_, access_method=method, is_active=active,
                          check_frequency=timedelta(days=1), terms_status="allowed", notes=notes),
        )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
        ("sources", "0001_initial"),
    ]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
