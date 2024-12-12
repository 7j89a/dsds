# استخدم صورة Python الأساسية
FROM python:3.9-slim

# تعيين الدليل العمل داخل الحاوية
WORKDIR /app

# نسخ ملفات المشروع إلى الحاوية
COPY . /app

# تثبيت الاعتمادات المطلوبة
RUN pip install --no-cache-dir -r requirements.txt

# تعيين البيئة لتشغيل البوت
CMD ["python", "bot.py"]
