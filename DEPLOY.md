# راه‌اندازی روی سرور مجازی (مرحله‌ی ۶)

> این راهنما را فقط وقتی لازم دارید که بخواهید سایت را برای همه آنلاین کنید. برای دیدن سایت روی کامپیوتر خودتان به `WINDOWS.md` نگاه کنید.
> **توجه:** فایل‌های این بخش روی یک سرور واقعی هنوز آزمایش نشده‌اند. فقط روی یک کامپیوتر آزمایشی با gunicorn و تنظیمات سرور امتحان شده‌اند. بار اول که روی سرور اجرا می‌کنید، اگر خطایی آمد، متن خطا را برای من بفرستید.

## چه چیزی لازم است؟
1. **یک سرور مجازی (VPS)** با Ubuntu 24.04. مثلاً از Hetzner، DigitalOcean یا هر شرکت دیگر. یک سرور کوچک (۲ گیگابایت RAM) کافی است. قیمت را در سایت خود شرکت ببینید؛ پرداخت با کارت بانکی خودتان است و من نمی‌توانم آن را انجام بدهم.
2. **یک دامنه (اختیاری ولی بهتر)** مثل `example.com`. بدون دامنه سایت با آدرس IP و بدون HTTPS باز می‌شود، که فقط برای تست اولیه خوب است. با دامنه، گواهی HTTPS خودکار گرفته می‌شود. رکورد `A` دامنه را باید به IP سرور وصل کنید.
3. **دسترسی به مخزن GitHub** با «کلید فقط‌خواندنی» (Deploy key). اسکریپت نصب قدم‌به‌قدم می‌گوید چه کنید.

## نصب (یک بار)
1. از Windows در PowerShell به سرور وصل شوید (OpenSSH در Windows 10/11 هست):
   ```
   ssh root@آدرس-IP-سرور
   ```
2. در سرور:
   ```
   apt-get update && apt-get install -y git
   git clone https://github.com/ardacubuk22-blip/sayt-frosh-zahra.git /root/td
   ```
   چون مخزن Private است، این دستور رمز می‌خواهد. راه ساده‌تر: فقط فایل `deploy/setup_server.sh` را با `scp` از کامپیوتر خودتان به سرور بفرستید:
   ```
   scp deploy/setup_server.sh root@آدرس-IP-سرور:/root/
   ```
3. اجرای نصب (آدرس SSH مخزن را بدهید؛ دامنه اختیاری است):
   ```
   bash /root/setup_server.sh git@github.com:ardacubuk22-blip/sayt-frosh-zahra.git example.com
   ```
   وسط کار یک «کلید» نشان می‌دهد. آن را در GitHub به مخزن اضافه کنید: **Settings ← Deploy keys ← Add deploy key** (گزینه‌ی write access را **خاموش** بگذارید) و بعد Enter بزنید.
4. ساختن حساب مدیر:
   ```
   sudo -u turkiye /opt/turkiye-discover/.venv/bin/python /opt/turkiye-discover/manage.py createsuperuser
   ```
5. فایل تنظیمات `/opt/turkiye-discover/.env` را باز کنید (`nano /opt/turkiye-discover/.env`) و شماره‌ی واتساپ را بگذارید (`WHATSAPP_NUMBER=905551234567`). کلید API را هم وقتی گرفتید همین‌جا بگذارید. بعد:
   ```
   systemctl restart turkiye-discover
   ```
6. سایت را باز کنید، و `/healthz/` باید `ok` بدهد. پنل مدیریت در `/admin/` است.

## چه چیزی خودکار اجرا می‌شود؟
- **جمع‌آوری روزانه:** هر روز ساعت ۰۴:۰۰ به وقت استانبول (`turkiye-discover-collect.timer`). بدون کلید API فقط لینک‌ها پیدا می‌شوند و استخراج انجام نمی‌شود. وضعیت منابع در پنل مدیریت، بخش «منابع»، دیده می‌شود (هشدار برای صفر نتیجه یا خطا).
- **پشتیبان‌گیری روزانه از دیتابیس:** ساعت ۰۳:۳۰ در `/var/backups/turkiye-discover/` (۱۴ روز آخر نگه داشته می‌شود). این پشتیبان روی همان سرور است؛ اگر سرور از بین برود، پشتیبان هم می‌رود. گاهی یک نسخه را به کامپیوتر خودتان بگیرید (`scp`) یا از Snapshot خود شرکت سرور استفاده کنید.
- **اجرای دستی جمع‌آوری:** `sudo -u turkiye /opt/turkiye-discover/.venv/bin/python /opt/turkiye-discover/manage.py run_sources --force`

## به‌روزرسانی سایت بعد از هر تغییر کد
```
sudo /opt/turkiye-discover/deploy/deploy.sh
```
این دستور کد جدید را از GitHub می‌گیرد، دیتابیس را به‌روز می‌کند و سایت را دوباره راه می‌اندازد. در پایان شماره‌ی نسخه‌ی قبلی را هم نشان می‌دهد؛ اگر چیزی خراب شد، با همان شماره به نسخه‌ی قبل برمی‌گردید (دستور آن در خروجی نوشته شده است).

## دیدن خطاها (لاگ‌ها)
- وب‌سایت: `journalctl -u turkiye-discover -n 100`
- جمع‌آوری: `journalctl -u turkiye-discover-collect -n 100`
- وضعیت تایمرها: `systemctl list-timers | grep turkiye`
