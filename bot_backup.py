import json
import os
from datetime import datetime
from enum import IntEnum
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, ConversationHandler, filters
)
import logging

# === الإعدادات ===
import os
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = {7855827103}  # ← ضع user_id الخاص بك هنا (مثال: {987654321})

# ملف تخزين الحجوزات
BOOKINGS_FILE = "bookings.json"

# States
class State(IntEnum):
    NAME = 0
    PHONE = 1
    SERVICE = 2
    DAY = 3
    TIME_SLOT = 4
    EMERGENCY = 5

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === دوال مساعدة ===
def load_bookings():
    if os.path.exists(BOOKINGS_FILE):
        with open(BOOKINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_bookings(bookings):
    with open(BOOKINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(bookings, f, ensure_ascii=False, indent=2)

def update_booking(user_id, data):
    bookings = load_bookings()
    bookings[str(user_id)] = data
    save_bookings(bookings)

def delete_booking(user_id):
    bookings = load_bookings()
    bookings.pop(str(user_id), None)
    save_bookings(bookings)

# === واجهة المريض ===
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 حجز موعد جديد", callback_data='book')],
        [InlineKeyboardButton("ℹ️ معلومات عن المركز", callback_data='about_center')],
        [InlineKeyboardButton("🎥 فيديو توضيحي", callback_data='video')],
        [InlineKeyboardButton("📋 معلومات قبل التصوير", callback_data='before_imaging')],
        [InlineKeyboardButton("📍 الموقع والتواصل", callback_data='location')],
        [InlineKeyboardButton("🦷 حجوزاتي", callback_data='my_bookings')],
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in ADMIN_IDS:
        await admin_menu(update, context)
        return

    caption = (
        "🦷✨ **مرحبًا بك في عائلة مركز أمل!**\n\n"
        "دقة عالمية في كل لقطة، لأن ابتسامتك تستحق الأفضل! 🌟"
    )
    await update.message.reply_text(caption, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

# === واجهة المشرف ===
async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🔐 **لوحة تحكم المشرف**\nاختر إجراءً:"
    keyboard = [
        [InlineKeyboardButton("👁️ عرض الحجوزات", callback_data='admin_view')],
        [InlineKeyboardButton("🏠 العودة للقائمة", callback_data='back')],
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_view_bookings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    bookings = load_bookings()
    if not bookings:
        await query.edit_message_text("لا توجد حجوزات.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='admin_menu')]]))
        return

    keyboard = []
    for uid, data in bookings.items():
        name = data.get("name", "مجهول")
        time = data.get("time", "")
        service = data.get("service", "")
        status = data.get("status", "قيد الانتظار")
        keyboard.append([InlineKeyboardButton(f"{name} | {time} | {service}", callback_data=f"admin_edit_{uid}")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='admin_menu')])
    await query.edit_message_text("اختر حجزًا للإدارة:", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_edit_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.data.split("_")[-1]
    data = load_bookings().get(user_id, {})
    if not data:
        await query.edit_message_text("الحجز غير موجود.")
        return

    name = data.get("name", "مجهول")
    time = data.get("time", "")
    service = data.get("service", "")
    status = data.get("status", "قيد الانتظار")
    text = f"{name} | {time} | {service}\nالحالة: {status}"
    keyboard = [
        [InlineKeyboardButton("✅ تم التصوير", callback_data=f"admin_set_done_{user_id}")],
        [InlineKeyboardButton("❌ لم يحضر", callback_data=f"admin_set_absent_{user_id}")],
        [InlineKeyboardButton("🗑️ حذف الحجز", callback_data=f"admin_confirm_delete_{user_id}")],
        [InlineKeyboardButton("🔙 رجوع", callback_data='admin_view')],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# === إجراءات المشرف ===
async def admin_set_status(update: Update, context: ContextTypes.DEFAULT_TYPE, new_status: str):
    query = update.callback_query
    await query.answer()
    user_id = query.data.split("_")[-1]
    bookings = load_bookings()
    if user_id not in bookings:
        await query.edit_message_text("الحجز غير موجود.")
        return

    bookings[user_id]["status"] = new_status
    save_bookings(bookings)

    # إرسال تقييم إذا تم التصوير
    if new_status == "تم التصوير":
        rating_buttons = [
            [InlineKeyboardButton("⭐", callback_data=f"rate_1_{user_id}")],
            [InlineKeyboardButton("⭐⭐", callback_data=f"rate_2_{user_id}")],
            [InlineKeyboardButton("⭐⭐⭐", callback_data=f"rate_3_{user_id}")],
            [InlineKeyboardButton("⭐⭐⭐⭐", callback_data=f"rate_4_{user_id}")],
            [InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data=f"rate_5_{user_id}")]
        ]
        try:
            await context.bot.send_message(
                chat_id=int(user_id),
                text="أهلًا بك! 🌟\nنأمل أن تكون خدمتنا قد نالت رضاك.\nمن فضلك، خذ لحظة لتقييمنا:",
                reply_markup=InlineKeyboardMarkup(rating_buttons)
            )
        except:
            pass

    await query.edit_message_text(f"✅ تم التحديث إلى: **{new_status}**", parse_mode="Markdown")

async def admin_confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.data.split("_")[-1]
    keyboard = [
        [InlineKeyboardButton("نعم، احذف", callback_data=f"admin_delete_{user_id}")],
        [InlineKeyboardButton("إلغاء", callback_data=f"admin_edit_{user_id}")]
    ]
    await query.edit_message_text("هل أنت متأكد من الحذف؟", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_delete_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.data.split("_")[-1]
    delete_booking(user_id)
    await query.edit_message_text("🗑️ تم الحذف بنجاح.")

# === حجز موعد (للمريض) ===
async def book_appointment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text("من فضلك، أدخل **اسمك الكامل**: 👤")
    return State.NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("📞 من فضلك، أدخل **رقم جوالك**:")
    return State.PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = update.message.text
    keyboard = [
        [InlineKeyboardButton("📸 بانورامي", callback_data='تصوير بانورامي')],
        [InlineKeyboardButton("🦴 CBCT ثلاثي الأبعاد", callback_data='تصوير CBCT ثلاثي الأبعاد')],
        [InlineKeyboardButton("👃 الجيوب الأنفية", callback_data='تصوير الجيوب الأنفية')],
        [InlineKeyboardButton("🦷 مفصل الفك", callback_data='تصوير مفصل الفك')],
        [InlineKeyboardButton("🩺 غير متأكد", callback_data='غير متأكد')],
    ]
    await update.message.reply_text("ما نوع التصوير المطلوب؟", reply_markup=InlineKeyboardMarkup(keyboard))
    return State.SERVICE

async def get_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    selected = query.data
    context.user_data['service'] = selected

    days = ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"]
    keyboard = [[InlineKeyboardButton(day, callback_data=day)] for day in days]
    await query.message.reply_text("📅 **اختر اليوم المناسب لك:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return State.DAY

async def get_time_slot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['day'] = query.data
    time_slots = [
        "🕘 9:00 صباحًا", "🕙 10:00 صباحًا", "🕚 11:00 صباحًا",
        "🕛 12:00 ظهرًا", "🕐 1:00 مساءً", "🕑 2:00 مساءً",
        "🕒 3:00 مساءً", "🕓 4:00 مساءً", "🕔 5:00 مساءً",
        "🕕 6:00 مساءً", "🕖 7:00 مساءً", "🕗 8:00 مساءً"
    ]
    keyboard = [[InlineKeyboardButton(slot, callback_data=f"time_{slot}")] for slot in time_slots]
    await query.message.reply_text(f"⏰ **اختر الوقت في يوم {context.user_data['day']}:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return State.TIME_SLOT

async def get_emergency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    time_slot = query.data.replace("time_", "")
    context.user_data['time'] = time_slot
    keyboard = [
        [InlineKeyboardButton("⏰ عادي", callback_data='normal')],
        [InlineKeyboardButton("⚠️ طارئ", callback_data='emergency')],
    ]
    await query.message.reply_text("هل هذا موعد **عادي** أم **طارئ**؟", reply_markup=InlineKeyboardMarkup(keyboard))
    return State.EMERGENCY

async def confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    emergency_status = "طارئ" if query.data == 'emergency' else "عادي"
    current_date = datetime.now().strftime("%d/%m/%Y")

    summary = (
        "✅ **تم استلام طلب حجزك!**\n\n"
        f"👤 الاسم: {context.user_data['name']}\n"
        f"📞 الجوال: {context.user_data['phone']}\n"
        f"🦷 الخدمة: {context.user_data['service']}\n"
        f"📅 اليوم: {context.user_data['day']}\n"
        f"⏰ الوقت: {context.user_data['time']}\n"
        f"📆 التاريخ: {current_date}\n"
        f"🚨 النوع: {emergency_status}\n\n"
        "شكرًا لثقتكم بنا! 🌸\n"
        "سيتم التواصل معكم قريبًا لتأكيد الموعد."
    )
    user_id = update.effective_user.id
    booking_data = {
        "name": context.user_data['name'],
        "phone": context.user_data['phone'],
        "service": context.user_data['service'],
        "day": context.user_data['day'],
        "time": context.user_data['time'],
        "date": current_date,
        "type": emergency_status,
        "status": "قيد الانتظار"
    }
    update_booking(user_id, booking_data)

    await query.message.reply_text(summary, parse_mode="Markdown")
    return ConversationHandler.END

# === التقييم ===
async def handle_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("شكرًا لتقييمك! ❤️\nنحن فخورون بأنك اخترت **مركز أمل**!")

# === معالجة الأزرار ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == 'book':
        return await book_appointment(update, context)
    elif data == 'admin_menu':
        await admin_menu(update, context)
        return ConversationHandler.END
    elif data == 'admin_view':
        await admin_view_bookings(update, context)
        return ConversationHandler.END
    elif data.startswith('admin_edit_'):
        await admin_edit_booking(update, context)
        return ConversationHandler.END
    elif data.startswith('admin_set_done_'):
        await admin_set_status(update, context, "تم التصوير")
        return ConversationHandler.END
    elif data.startswith('admin_set_absent_'):
        await admin_set_status(update, context, "لم يحضر")
        return ConversationHandler.END
    elif data.startswith('admin_confirm_delete_'):
        await admin_confirm_delete(update, context)
        return ConversationHandler.END
    elif data.startswith('admin_delete_'):
        await admin_delete_booking(update, context)
        return ConversationHandler.END
    elif data.startswith('rate_'):
        await handle_rating(update, context)
        return ConversationHandler.END
    elif data == 'about_center':
        text = (
            "🏥 **مركز أمل للتصوير الشعاعي**\n\n"
            "في مركز أمل نقدم لك أحدث تقنيات التصوير الشعاعي للأسنان والفكين، بدقة عالمية تضمن وضوح التفاصيل من أول مرة.\n\n"
            "❌ **هل تعاني من تكرار التصوير بسبب ضعف الجودة؟**\n"
            "✅ مع مركز أمل لن تحتاج لإعادة التصوير مرة أخرى!\n\n"
            "**خدماتنا:**\n"
            "• 🦴 تصوير CBCT ثلاثي الأبعاد بأحدث الأجهزة\n"
            "• 📸 تصوير بانورامي دقيق يكشف كل التفاصيل\n"
            "• 👃 تصوير الجيوب الأنفية\n"
            "• 🦷 تصوير مفصل الفك\n\n"
            "✨ نتائج موثوقة يعتمد عليها الأطباء عالميًا\n\n"
            "📍 **الموقع:** نابلس - عسكر القديم - الشارع الرئيسي، مقابل مخبز أبو عبده\n"
            "📞 **للحجز:** [0569509093](tel:+970569509093)"
        )
        keyboard = [[InlineKeyboardButton("🏠 العودة للقائمة", callback_data='back')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return ConversationHandler.END
    
    elif data == 'video':
        text = (
            "🎥 **شاهد مركز أمل**\n\n"
            "تفضل بمشاهدة قناتنا على اليوتيوب للتعرف على المركز وخدماتنا:\n\n"
            "🔗 [قناة مركز أمل على اليوتيوب](https://youtube.com/@amal-xray-center)"
        )
        keyboard = [[InlineKeyboardButton("🏠 العودة للقائمة", callback_data='back')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown", disable_web_page_preview=False)
        return ConversationHandler.END
    
    elif data == 'before_imaging':
        text = (
            "📋 **معلومات مهمة قبل التصوير**\n\n"
            "للحصول على أفضل نتائج تصوير، يُرجى اتباع التعليمات التالية:\n\n"
            "✅ **قبل الحضور:**\n"
            "• لا حاجة للصيام قبل التصوير\n"
            "• ارتدِ ملابس مريحة\n"
            "• أحضر معك أي تصاوير سابقة (إن وجدت)\n\n"
            "⚠️ **يُرجى إزالة:**\n"
            "• المجوهرات والأقراط\n"
            "• النظارات\n"
            "• دبابيس الشعر المعدنية\n"
            "• أطقم الأسنان المتحركة\n\n"
            "🤰 **للسيدات الحوامل:**\n"
            "• يُرجى إخبار الفني قبل التصوير\n\n"
            "📞 **لأي استفسار:** 0569509093"
        )
        keyboard = [[InlineKeyboardButton("🏠 العودة للقائمة", callback_data='back')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return ConversationHandler.END
    
    elif data == 'location':
        text = (
            "📍 **موقع مركز أمل**\n\n"
            "**العنوان:**\n"
            "نابلس - عسكر القديم - الشارع الرئيسي\n"
            "مقابل مخبز أبو عبده\n\n"
            "🕘 **ساعات العمل:**\n"
            "من 9:00 صباحًا - 8:00 مساءً\n"
            "جميع أيام الأسبوع\n\n"
            "📞 **للحجز والاستفسار:**\n"
            "[0569509093](tel:+970569509093)\n\n"
            "🗺️ **خريطة الموقع:**\n"
            "[افتح الموقع في خرائط Google](https://www.google.com/maps/place/32%C2%B013'17.7%22N+35%C2%B017'51.4%22E/@32.221585,35.297612,17z)"
        )
        keyboard = [[InlineKeyboardButton("🏠 العودة للقائمة", callback_data='back')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return ConversationHandler.END
    
    elif data == 'my_bookings':
        user_id = str(update.effective_user.id)
        bookings = load_bookings()
        user_booking = bookings.get(user_id)
        
        if not user_booking:
            text = "📭 **لا توجد حجوزات**\n\nليس لديك أي حجوزات حالياً.\nيمكنك حجز موعد جديد من القائمة الرئيسية."
        else:
            status_emoji = {
                "قيد الانتظار": "⏳",
                "مؤكد": "✅",
                "تم التصوير": "✔️",
                "لم يحضر": "❌"
            }
            status = user_booking.get("status", "قيد الانتظار")
            emoji = status_emoji.get(status, "📋")
            
            text = (
                f"{emoji} **حجزك الحالي**\n\n"
                f"👤 الاسم: {user_booking.get('name', 'غير محدد')}\n"
                f"📞 الجوال: {user_booking.get('phone', 'غير محدد')}\n"
                f"🦷 نوع التصوير: {user_booking.get('service', 'غير محدد')}\n"
                f"📅 اليوم: {user_booking.get('day', 'غير محدد')}\n"
                f"⏰ الوقت: {user_booking.get('time', 'غير محدد')}\n"
                f"📆 التاريخ: {user_booking.get('date', 'غير محدد')}\n"
                f"🚨 النوع: {user_booking.get('type', 'غير محدد')}\n"
                f"📊 الحالة: **{status}**\n\n"
            )
            
            if status == "قيد الانتظار":
                text += "⏳ سيتم التواصل معك قريباً لتأكيد الموعد."
            elif status == "مؤكد":
                text += "✅ موعدك مؤكد! ننتظرك."
            elif status == "تم التصوير":
                text += "✔️ تم إنجاز التصوير بنجاح. شكراً لزيارتك!"
        
        keyboard = [
            [InlineKeyboardButton("🗑️ إلغاء الحجز", callback_data='cancel_my_booking')],
            [InlineKeyboardButton("🏠 العودة للقائمة", callback_data='back')]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return ConversationHandler.END
    
    elif data == 'cancel_my_booking':
        user_id = str(update.effective_user.id)
        keyboard = [
            [InlineKeyboardButton("نعم، إلغاء الحجز", callback_data='confirm_cancel_my_booking')],
            [InlineKeyboardButton("لا، العودة", callback_data='my_bookings')]
        ]
        await query.edit_message_text(
            "⚠️ **هل أنت متأكد من إلغاء حجزك؟**\n\nلن يمكنك التراجع عن هذا الإجراء.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    
    elif data == 'confirm_cancel_my_booking':
        user_id = str(update.effective_user.id)
        delete_booking(user_id)
        text = "✅ **تم إلغاء حجزك بنجاح**\n\nيمكنك حجز موعد جديد في أي وقت."
        keyboard = [[InlineKeyboardButton("🏠 العودة للقائمة", callback_data='back')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return ConversationHandler.END
    
    elif data == 'back':
        caption = (
            "🦷✨ **مرحبًا بك في عائلة مركز أمل!**\n\n"
            "دقة عالمية في كل لقطة، لأن ابتسامتك تستحق الأفضل! 🌟"
        )
        await query.edit_message_text(caption, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
        return ConversationHandler.END
    else:
        text = "جارٍ التحميل..."
        keyboard = [[InlineKeyboardButton("🏠 العودة للقائمة", callback_data='back')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return ConversationHandler.END

# === التشغيل ===
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # ConversationHandler يجب أن يُضاف قبل button_handler
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern='^book$')],
        states={
            State.NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            State.PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            State.SERVICE: [CallbackQueryHandler(get_day)],
            State.DAY: [CallbackQueryHandler(get_time_slot)],
            State.TIME_SLOT: [CallbackQueryHandler(get_emergency)],
            State.EMERGENCY: [CallbackQueryHandler(confirm_booking)],
        },
        fallbacks=[CommandHandler('cancel', lambda u, c: u.message.reply_text("تم الإلغاء."))]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)  # ← يجب أن يكون قبل button_handler
    application.add_handler(CallbackQueryHandler(button_handler))

    application.run_polling()

if __name__ == '__main__':
    main()