from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from moviepy.video.io.VideoFileClip import VideoFileClip  # لحساب مدة الفيديو
import subprocess
import os
import time

# بيانات الاتصال بالبوت
api_id = 20944746  # استبدل بـ API ID الخاص بك
api_hash = "d169162c1bcf092a6773e685c62c3894"  # استبدل بـ API Hash الخاص بك
bot_token = "YOUR_BOT_TOKEN"  # استبدل بـ توكن البوت الخاص بك

# تشغيل البوت
app = Client("vidsseo_downloader_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

thumbnail_path = "/workspaces/VPS/photo_2024-11-09_19-12-35 (1).jpg"
# متغيرات عالمية
user_headers = {}
user_states = {}

@app.on_message(filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id
    user_states[user_id] = "idle"
    await message.reply_text(
        "مرحبًا بك! أرسل لي رابط الفيديو الذي تريد تنزيله.\n\n"
        "يمكنك أيضًا تخصيص الهيدرز (مثل User-Agent وReferer) باستخدام الأزرار أدناه.",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("تحديد User-Agent", callback_data="user_agent"),
                InlineKeyboardButton("تحديد Referer", callback_data="referer")
            ]
        ])
    )

@app.on_message(filters.text & ~filters.command("start"))
async def handle_message(client, message):
    user_id = message.from_user.id
    text = message.text.strip()

    state = user_states.get(user_id, "idle")

    if state == "set_user_agent":
        user_headers.setdefault(user_id, {})['User-Agent'] = text
        user_states[user_id] = "idle"
        await message.reply_text(f"تم تعيين User-Agent إلى: {text}")
    elif state == "set_referer":
        if text.startswith("http://") or text.startswith("https://"):
            user_headers.setdefault(user_id, {})['Referer'] = text
            user_states[user_id] = "idle"
            await message.reply_text(f"تم تعيين Referer إلى: {text}")
        else:
            await message.reply_text("القيمة المدخلة غير صالحة. يرجى إدخال رابط Referer صالح.")
    elif state == "idle":
        if text.startswith("http://") or text.startswith("https://"):
            headers = user_headers.get(user_id, {})
            output_file = f"{user_id}_video.mp4"
            command = [
                'yt-dlp',
                '--no-check-certificate',
                '-N', '20',
                '-o', output_file
            ]

            # إضافة الهيدرز إذا تم تعيينها
            if 'User-Agent' in headers:
                command.extend(['--add-header', f'User-Agent: {headers["User-Agent"]}'])
            if 'Referer' in headers:
                command.extend(['--add-header', f'Referer: {headers["Referer"]}'])

            command.append(text)

            try:
                progress_message = await message.reply_text("⌛ جاري التنزيل...")

                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='utf-8'
                )

                last_update_time = time.time()

                while True:
                    output = process.stdout.readline()
                    if output == "" and process.poll() is not None:
                        break
                    if output:
                        current_time = time.time()
                        if "%" in output or "Downloading" in output:
                            if current_time - last_update_time >= 5:
                                await progress_message.edit(f"⌛ {output.strip()}")
                                last_update_time = current_time

                if process.returncode == 0:
                    # حساب مدة الفيديو
                    duration = get_video_duration(output_file)

                    await progress_message.edit(
                        f"✅ تم تنزيل الفيديو بنجاح! (مدة الفيديو: {duration} ثانية)\n"
                        "⌛ جاري رفع الفيديو إلى Telegram..."
                    )
                    await upload_with_progress(client, progress_message, output_file, "🎥 تم التنزيل بنجاح!", duration)
                    os.remove(output_file)
                else:
                    await progress_message.edit("❌ حدث خطأ أثناء التنزيل.")
            except Exception as e:
                await message.reply_text(f"❌ خطأ أثناء تنفيذ yt-dlp: {str(e)}")
        else:
            await message.reply_text("الرجاء إرسال رابط فيديو صالح للتنزيل.")


async def upload_with_progress(client, progress_message, file_path, caption, duration):
    """دالة لرفع الملف كفيديو مع عرض نسبة التقدم كل 5 ثوانٍ وبدفعات ثابتة"""
    total_size = os.path.getsize(file_path)
    last_update_time = time.time()
    last_percent = 0

    async def progress_callback(current, total):
        nonlocal last_percent, last_update_time
        percent = int((current / total_size) * 100)
        current_time = time.time()

        if current_time - last_update_time >= 10 or percent >= last_percent + 20:
            await progress_message.edit(f"📤 جاري الرفع... {percent}%")
            last_percent = percent
            last_update_time = current_time

    await client.send_video(
        chat_id=progress_message.chat.id,
        video=file_path,
        width=640,
        height=360,
        duration=duration,  # إضافة مدة الفيديو هنا
        thumb=thumbnail_path,
        caption=caption,
        supports_streaming=True,
        progress=progress_callback
    )


def get_video_duration(video_path):
    """دالة لحساب مدة الفيديو باستخدام moviepy"""
    try:
        with VideoFileClip(video_path) as video_clip:
            duration = int(video_clip.duration)
            return duration
    except Exception as e:
        print(f"Error calculating video duration: {str(e)}")
        return 0


@app.on_callback_query()
async def handle_callback_query(client, callback_query):
    user_id = callback_query.from_user.id
    data = callback_query.data

    if data == "user_agent":
        user_states[user_id] = "set_user_agent"
        await callback_query.message.reply_text("أدخل قيمة User-Agent:")
    elif data == "referer":
        user_states[user_id] = "set_referer"
        await callback_query.message.reply_text("أدخل قيمة Referer:")


# بدء تشغيل البوت
if __name__ == "__main__":
    print("Bot is running...")
    app.run()
