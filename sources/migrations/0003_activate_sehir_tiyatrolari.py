from django.db import migrations


def activate(apps, schema_editor):
    Source = apps.get_model("sources", "Source")
    Source.objects.filter(adapter="sehir_tiyatrolari").update(
        is_active=True,
        notes="بررسی‌شده: HTML ثابت، تاریخ و سالن در متن صفحه است. فقط با آدرس بدون www کار می‌کند.",
    )
    Source.objects.filter(adapter="akm").update(
        notes="صفحه‌ی رویداد با جاوااسکریپت (Next.js) پر می‌شود و متن ثابت ندارد؛ تا پیدا شدن راه خواندن داده غیرفعال می‌ماند.",
    )
    Source.objects.filter(adapter="iksv").update(
        notes="رویدادها در زیرسایت هر جشنواره (film/caz/muzik/tiyatro.iksv.org) و بیشتر با جاوااسکریپت است؛ بلیت‌ها در Passo. نیازمند بررسی جدا.",
    )
    Source.objects.filter(adapter="ibb_ckan").update(
        notes="robots.txt سایت مسیر /api/ را برای خزنده‌ها ممنوع کرده؛ تا تصمیم صاحب پروژه غیرفعال می‌ماند.",
    )


class Migration(migrations.Migration):
    dependencies = [("sources", "0002_seed_sources")]
    operations = [migrations.RunPython(activate, migrations.RunPython.noop)]
