# راهنمای اجرای پروژه روی Windows

این کارها را **فقط یک بار** انجام می‌دهید (بخش «هر بار» را پایین ببینید).
همه‌ی دستورها را در **PowerShell** بزنید (دکمه‌ی Start ← تایپ کنید PowerShell ← Enter).

## ۱. نصب Python (حدود ۳۰ مگابایت)
1. به https://www.python.org/downloads/ بروید و دکمه‌ی زرد **Download Python 3.13** را بزنید.
2. فایل را اجرا کنید. **حتماً تیک `Add python.exe to PATH` را در پایین پنجره بزنید**، بعد **Install Now**.
3. PowerShell را ببندید و دوباره باز کنید و بزنید:
   ```
   python --version
   ```
   باید چیزی مثل `Python 3.13.x` ببینید.

## ۲. نصب Git
1. به https://git-scm.com/download/win بروید و نسخه‌ی **64-bit Git for Windows Setup** را دانلود کنید.
2. نصب کنید و همه‌ی گزینه‌ها را روی پیش‌فرض بگذارید (فقط Next بزنید).
3. PowerShell را دوباره باز کنید و بزنید:
   ```
   git --version
   ```

## ۳. گرفتن کد از GitHub
```
cd $HOME\Documents
git clone https://github.com/ardacubuk22-blip/SAYT-FROSH-ZAHRA.git
cd SAYT-FROSH-ZAHRA
git checkout claude/turkiye-discover-planning-ahb87a
```
چون مخزن Private است، بار اول یک پنجره‌ی مرورگر باز می‌شود تا با حساب GitHub وارد شوید. این کار را تأیید کنید.

## ۴. آماده‌سازی پروژه
```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
notepad .env
```
- اگر خطای «running scripts is disabled» گرفتید، یک بار این را بزنید و بعد دوباره `Activate.ps1` را اجرا کنید:
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
- در Notepad جلوی `ANTHROPIC_API_KEY=` کلید API خودتان را بگذارید و فایل را ذخیره کنید. این فایل هرگز به GitHub نمی‌رود.

## ۵. ساخت دیتابیس و حساب مدیر
```
python manage.py migrate
python manage.py createsuperuser
```
یک نام کاربری و رمز برای پنل مدیریت انتخاب کنید (ایمیل را می‌توانید خالی بگذارید).

## ۶. روشن کردن سایت
```
python manage.py runserver
```
- سایت: http://127.0.0.1:8000
- پنل مدیریت: http://127.0.0.1:8000/admin
- برای خاموش کردن: در PowerShell کلید `Ctrl + C`.
- **مهم:** آدرس `127.0.0.1` یعنی «همین دستگاه». پس این آدرس فقط در مرورگرِ همان کامپیوتری باز می‌شود که سایت روی آن روشن است، نه روی گوشی.

### دیدن سایت روی گوشی
1. گوشی و کامپیوتر باید به **یک Wi-Fi** وصل باشند (اینترنت موبایل کار نمی‌کند).
2. سایت را این‌طور روشن کنید:
   ```
   python manage.py runserver 0.0.0.0:8000
   ```
3. در یک PowerShell دیگر بزنید `ipconfig` و عدد جلوی **IPv4 Address** را پیدا کنید (مثلاً `192.168.1.25`).
4. در مرورگر گوشی بزنید: `http://192.168.1.25:8000` (عدد خودتان را بگذارید).
5. اگر Windows پرسید «Allow access?» برای Python، گزینه‌ی **Private networks** را تأیید کنید.

### دیدن سایت با رویداد و تور نمونه (بدون نیاز به کلید API)
```
python manage.py seed_demo
```
پنج رویداد و دو تور ساختگی اضافه می‌شود. بعد از دیدن سایت، با این دستور پاکشان کنید:
```
python manage.py seed_demo --remove
```
شماره‌ی واتساپ در فایل `.env` با `WHATSAPP_NUMBER=` تنظیم می‌شود (فعلاً PHONE_NUMBER است).

## ۷. اجرای جمع‌آوری (در یک PowerShell دیگر)
```
cd $HOME\Documents\SAYT-FROSH-ZAHRA
.venv\Scripts\Activate.ps1
python manage.py run_sources --source kultursanat --force --limit 5
```
`--limit 5` یعنی فقط ۵ صفحه بررسی شود تا هزینه‌ی API کم بماند.

---

## هر بار که می‌خواهید کار کنید
```
cd $HOME\Documents\SAYT-FROSH-ZAHRA
git pull
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```
`git pull` آخرین تغییرات را از GitHub می‌گیرد. دو دستور بعدی اگر چیز جدیدی نباشد، کاری انجام نمی‌دهند.
