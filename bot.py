#!/usr/bin/env python3
# coding: utf-8

"""
Bot.py — بوت مركز أمل للتصوير الشعاعي
نسخة شاملة مع جميع التحسينات المطلوبة
"""

import os
import logging
from datetime import datetime, timedelta
from enum import IntEnum
import json
import requests

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

import database as db

# -----------------------
# إعدادات عامة
# -----------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = {7855827103}

# حالات ConversationHandler
class State(IntEnum):
    NAME = 0
    PHONE = 1
    SERVICE = 2
    DAY = 3
    TIME_SLOT = 4
    EMERGENCY = 5
    RATING_FEEDBACK = 6
    FAQ = 7
    MULTI_SERVICE = 8
    WEATHER_CONFIRM = 9
    WAITING_LIST = 10
    USER_PREFERENCES = 11

# -----------------------
# نظام الموضوعات الموسمية
# -----------------------
class ThemeManager:
    def __init__(self):
        self.current_theme = self._detect_theme()
    
    def _detect_theme(self):
        now = datetime.now()
        month = now.month
        
        if month == 3:
            return "ramadan"
        elif month == 4:
            return "eid"
        elif month in [12, 1, 2]:
            return "winter"
        elif month in [6, 7, 8]:
            return "summer"
        else:
            return "default"
    
    def get_theme_config(self):
        themes = {
            "default": {
                "colors": {"primary": "🦷", "secondary": "✨"},
                "welcome_message": "🦷✨ **مرحبًا بك في عائلة مركز أمل!**\n\nدقة عالمية في كل لقطة، لأن ابتسامتك تستحق الأفضل! 🌟",
                "icons": {
                    "booking": "📅", "info": "ℹ️", "video": "🎥", 
                    "instructions": "📋", "location": "📍", "bookings": "🦷"
                }
            },
            "ramadan": {
                "colors": {"primary": "🌙", "secondary": "✨"},
                "welcome_message": "🌙✨ **رمضان كريم من عائلة مركز أمل!**\n\nفي هذا الشهر الفضيل، نتمنى لكم صحة وابتسامة مشرقة! 🕌",
                "icons": {
                    "booking": "🌙", "info": "📖", "video": "🎬", 
                    "instructions": "📋", "location": "🕌", "bookings": "🦷"
                }
            },
            "winter": {
                "colors": {"primary": "❄️", "secondary": "🦷"},
                "welcome_message": "❄️🦷 **مرحبًا بكم في مركز أمل!**\n\nمع برودة الطقس، اهتموا بصحتكم وابتسامتكم! 🌨️",
                "icons": {
                    "booking": "❄️", "info": "ℹ️", "video": "🎥", 
                    "instructions": "🧤", "location": "🏔️", "bookings": "🦷"
                }
            },
            "summer": {
                "colors": {"primary": "☀️", "secondary": "🦷"},
                "welcome_message": "☀️🦷 **مرحبًا بكم في مركز أمل!**\n\nمع ارتفاع الحرارة، حافظوا على رطوبة أجسامكم! 🌊",
                "icons": {
                    "booking": "☀️", "info": "ℹ️", "video": "🎥", 
                    "instructions": "😎", "location": "🏖️", "bookings": "🦷"
                }
            }
        }
        return themes.get(self.current_theme, themes["default"])

# -----------------------
# نظام الأسئلة الشائعة
# -----------------------
class FAQManager:
    def __init__(self):
        self.faq_data = {
            "duration": {
                "question": "⏱️ كم تستغرق جلسة التصوير؟",
                "answer": "• البانوراما: 10-15 دقيقة\n• CBCT: 15-20 دقيقة\n• الجيوب الأنفية: 10 دقائق\n• مفصل الفك: 15 دقيقة"
            },
            "preparation": {
                "question": "📝 هل هناك تحضيرات مطلوبة قبل التصوير؟",
                "answer": "• لا حاجة للصيام\n• إزالة المجوهرات والنظارات\n• إحضار أي تصاوير سابقة\n• إخبار الفني في حالة الحمل"
            },
            "working_hours": {
                "question": "🕘 ما هي أوقات العمل؟",
                "answer": "⏰ من 9:00 صباحاً - 8:00 مساءً\n📅 جميع أيام الأسبوع"
            },
            "emergency": {
                "question": "🚨 هل تقدمون خدمة الطوارئ؟",
                "answer": "نعم! لدينا خدمة الطوارئ للمواقف المستعجلة. اختر 'طارئ' أثناء الحجز"
            },
            "results": {
                "question": "📄 متى تظهر النتائج؟",
                "answer": "• النتائج فورية في معظم الحالات\n• نسخة رقمية عبر البوت (قريباً)\n• تقرير مفصل للطبيب المعالج"
            },
            "pricing": {
                "question": "💰 ما هي أسعار الخدمات؟",
                "answer": "• البانوراما: 50 شيكل\n• CBCT: 150 شيكل\n• الجيوب الأنفية: 80 شيكل\n• مفصل الفك: 100 شيكل"
            }
        }
    
    def get_faq_keyboard(self):
        keyboard = []
        for key, faq in self.faq_data.items():
            keyboard.append([InlineKeyboardButton(faq["question"], callback_data=f"faq_{key}")])
        keyboard.append([InlineKeyboardButton("🏠 العودة للقائمة", callback_data='back')])
        return InlineKeyboardMarkup(keyboard)
    
    def get_faq_answer(self, faq_key):
        faq = self.faq_data.get(faq_key)
        if faq:
            return f"**{faq['question']}**\n\n{faq['answer']}"
        return "❌ السؤال غير موجود."

# -----------------------
# نظام الانتظار الذكي
# -----------------------
class WaitingListManager:
    def __init__(self):
        self.waiting_list = {}
    
    def add_to_waiting_list(self, user_id, user_data):
        self.waiting_list[user_id] = {
            'name': user_data.get('name'),
            'phone': user_data.get('phone'),
            'service': user_data.get('service'),
            'timestamp': datetime.now()
        }
    
    def remove_from_waiting_list(self, user_id):
        return self.waiting_list.pop(user_id, None)
    
    def get_waiting_list(self):
        return self.waiting_list
    
    async def notify_waiting_users(self, context, day_name, available_slots):
        users_to_remove = []
        for user_id, user_data in self.waiting_list.items():
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        "🎉 **أوقات جديدة متاحة!**\n\n"
                        f"عزيزي/عزيزتي {user_data['name']}\n"
                        "هناك أوقات متاحة الآن للحجز.\n\n"
                        f"🦷 الخدمة المطلوبة: {user_data['service']}\n"
                        f"📅 اليوم: {day_name}\n"
                        "⏰ الأوقات المتاحة:\n" + 
                        "\n".join([f"• {slot}" for slot in available_slots[:3]]) +
                        "\n\nسارع بالحجز قبل أن تنتهي! 🚀\n"
                        "استخدم /start للبدء"
                    ),
                    parse_mode="Markdown"
                )
                users_to_remove.append(user_id)
                logger.info(f"Notified waiting user {user_id} about available slots")
            except Exception as e:
                logger.error(f"Failed to notify waiting user {user_id}: {e}")
        
        for user_id in users_to_remove:
            self.remove_from_waiting_list(user_id)

# -----------------------
# نظام حفظ البيانات
# -----------------------
class UserDataManager:
    def __init__(self):
        self.user_preferences = {}
    
    def save_user_data(self, user_id, name, phone):
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {}
        
        self.user_preferences[user_id].update({
            'name': name,
            'phone': phone,
            'last_booking': datetime.now(),
            'booking_count': self.user_preferences[user_id].get('booking_count', 0) + 1
        })
    
    def get_user_data(self, user_id):
        return self.user_preferences.get(user_id, {})
    
    def has_previous_data(self, user_id):
        return user_id in self.user_preferences and 'name' in self.user_preferences[user_id]

# -----------------------
# نظام الطقس
# -----------------------
class WeatherManager:
    def __init__(self):
        self.api_key = os.getenv("WEATHER_API_KEY")
    
    async def get_weather_alert(self):
        if not self.api_key:
            return None
        
        try:
            # مثال لاستدعاء API الطقس (يمكن استبداله بأي API)
            response = requests.get(
                f"http://api.openweathermap.org/data/2.5/weather?q=Nablus&appid={self.api_key}&units=metric&lang=ar"
            )
            if response.status_code == 200:
                data = response.json()
                weather = data['weather'][0]['description']
                temp = data['main']['temp']
                
                if 'rain' in weather.lower() or 'storm' in weather.lower():
                    return f"⚠️ **تنبيه الطقس**: {weather}\n🌡️ درجة الحرارة: {temp}°C\nننصح بتأجيل الموعد إذا كانت الظروف صعبة"
                elif temp > 35:
                    return f"🌡️ **طقس حار**: {weather}\nدرجة الحرارة: {temp}°C\nننصح بشرب الماء والاحتماء من الشمس"
                elif temp < 5:
                    return f"❄️ **طقس بارد**: {weather}\nدرجة الحرارة: {temp}°C\nننصح بارتداء ملابس دافئة"
            
        except Exception as e:
            logger.error(f"Weather API error: {e}")
        
        return None

# -----------------------
# نظام الإشعارات المخصصة
# -----------------------
class NotificationManager:
    def __init__(self):
        self.user_preferences = {}
    
    def set_user_preferences(self, user_id, preferences):
        self.user_preferences[user_id] = preferences
    
    def get_user_preferences(self, user_id):
        return self.user_preferences.get(user_id, {
            'morning_notifications': True,
            'evening_notifications': True,
            'weather_alerts': True,
            'promotions': False
        })

# -----------------------
# إعدادات النظام
# -----------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# تهيئة جميع المدراء
theme_manager = ThemeManager()
faq_manager = FAQManager()
waiting_manager = WaitingListManager()
user_data_manager = UserDataManager()
weather_manager = WeatherManager()
notification_manager = NotificationManager()

# تهيئة قاعدة البيانات
db.init_database()

# -----------------------
# وظائف المساعدة مع السمات
# -----------------------
def main_menu_keyboard():
    theme = theme_manager.get_theme_config()
    icons = theme["icons"]
    
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{icons['booking']} حجز موعد جديد", callback_data='book')],
        [InlineKeyboardButton(f"{icons['info']} معلومات عن المركز", callback_data='about_center')],
        [InlineKeyboardButton(f"{icons['video']} فيديو توضيحي", callback_data='video')],
        [InlineKeyboardButton(f"{icons['instructions']} معلومات قبل التصوير", callback_data='before_imaging')],
        [InlineKeyboardButton(f"{icons['location']} الموقع والتواصل", callback_data='location')],
        [InlineKeyboardButton("📺 قناتنا على اليوتيوب", url='https://www.youtube.com/@amal-xray-center')],
        [InlineKeyboardButton("قناتنا على الفيسبوك", url='https://www.facebook.com/amal.xray.center/')],
        [InlineKeyboardButton(f"{icons['bookings']} حجوزاتي", callback_data='my_bookings')],
        [InlineKeyboardButton("❓ الأسئلة الشائعة", callback_data='faq_menu')],
        [InlineKeyboardButton("⚙️ تفضيلاتي", callback_data='user_preferences')],
    ])

def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            if update.callback_query:
                await update.callback_query.answer("❌ هذه الميزة مخصصة للمشرفين فقط.", show_alert=True)
            else:
                await update.message.reply_text("❌ هذه الميزة مخصصة للمشرفين فقط.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# -----------------------
# START / MAIN MENU
# -----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id in ADMIN_IDS and update.message is None and update.callback_query:
        await admin_menu(update, context)
        return

    theme = theme_manager.get_theme_config()
    
    # التحقق من تنبيهات الطقس
    weather_alert = await weather_manager.get_weather_alert()
    if weather_alert:
        if update.message:
            await update.message.reply_text(weather_alert, parse_mode="Markdown")
        else:
            await update.callback_query.message.reply_text(weather_alert, parse_mode="Markdown")
    
    if update.message:
        await update.message.reply_text(theme["welcome_message"], reply_markup=main_menu_keyboard(), parse_mode="Markdown")
    else:
        await update.callback_query.edit_message_text(theme["welcome_message"], reply_markup=main_menu_keyboard(), parse_mode="Markdown")

# -----------------------
# ADMIN MENU & ACTIONS
# -----------------------
async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🔐 **لوحة تحكم المشرف**\nاختر إجراءً:"
    keyboard = [
        [InlineKeyboardButton("👁️ عرض جميع الحجوزات", callback_data='admin_view')],
        [InlineKeyboardButton("⏳ الحجوزات المعلقة", callback_data='admin_pending')],
        [InlineKeyboardButton("📊 التقارير والإحصائيات", callback_data='admin_stats')],
        [InlineKeyboardButton("⭐ التقييمات", callback_data='admin_ratings')],
        [InlineKeyboardButton("📋 قائمة الانتظار", callback_data='admin_waiting_list')],
        [InlineKeyboardButton("👥 بيانات المستخدمين", callback_data='admin_user_data')],
        [InlineKeyboardButton("🏠 العودة للقائمة", callback_data='back')],
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def admin_view_bookings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    bookings = db.get_all_bookings()
    if not bookings:
        await query.edit_message_text("لا توجد حجوزات.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='admin_menu')]]))
        return

    keyboard = []
    for booking in bookings:
        uid = booking.get('user_id')
        name = booking.get('name', 'مجهول')
        time = booking.get('time', 'غير محدد')
        service = booking.get('service', 'غير محدد')
        status = booking.get('status', 'غير محدد')
        status_emoji = {"قيد الانتظار": "⏳", "مؤكد": "✅", "تم التصوير": "✔️", "لم يحضر": "❌"}.get(status, "📋")
        keyboard.append([InlineKeyboardButton(f"{status_emoji} {name} | {time} | {service}", callback_data=f"admin_edit_{uid}")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='admin_menu')])
    await query.edit_message_text("اختر حجزًا للإدارة:", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_pending_bookings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    bookings = db.get_pending_bookings()
    if not bookings:
        await query.edit_message_text("لا توجد حجوزات معلقة.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='admin_menu')]]))
        return

    keyboard = []
    for booking in bookings:
        uid = booking.get('user_id')
        name = booking.get('name', 'مجهول')
        time = booking.get('time', 'غير محدد')
        service = booking.get('service', 'غير محدد')
        keyboard.append([InlineKeyboardButton(f"⏳ {name} | {time} | {service}", callback_data=f"admin_edit_{uid}")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='admin_menu')])
    await query.edit_message_text("الحجوزات المعلقة (تحتاج تأكيد):", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_edit_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        user_id = int(query.data.split("_")[-1])
    except Exception:
        await query.edit_message_text("خطأ: لم يتم تحديد الحجز.")
        return

    booking = db.get_booking(user_id)
    if not booking:
        await query.edit_message_text("الحجز غير موجود.")
        return

    status = booking.get('status', 'غير محدد')
    status_emoji = {"قيد الانتظار": "⏳", "مؤكد": "✅", "تم التصوير": "✔️", "لم يحضر": "❌"}.get(status, "📋")

    text = (
        f"{status_emoji} **تفاصيل الحجز**\n\n"
        f"👤 الاسم: {booking.get('name','غير معروف')}\n"
        f"📞 الجوال: {booking.get('phone','-')}\n"
        f"🦷 الخدمة: {booking.get('service','-')}\n"
        f"📅 اليوم: {booking.get('day','-')}\n"
        f"⏰ الوقت: {booking.get('time','-')}\n"
        f"📆 التاريخ: {booking.get('date','-')}\n"
        f"🚨 النوع: {booking.get('type','-')}\n"
        f"📊 الحالة: **{status}**"
    )

    keyboard = []
    if status == "قيد الانتظار":
        keyboard.append([InlineKeyboardButton("✅ تأكيد الحجز", callback_data=f"admin_confirm_{user_id}")])
    if status in ["قيد الانتظار", "مؤكد"]:
        keyboard.append([InlineKeyboardButton("✔️ تم التصوير", callback_data=f"admin_set_done_{user_id}")])
        keyboard.append([InlineKeyboardButton("❌ لم يحضر", callback_data=f"admin_set_absent_{user_id}")])
    keyboard.append([InlineKeyboardButton("🗑️ حذف الحجز", callback_data=f"admin_confirm_delete_{user_id}")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='admin_view')])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def admin_confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        user_id = int(query.data.split("_")[-1])
    except Exception:
        await query.edit_message_text("حدث خطأ أثناء تأكيد الحجز.")
        return

    db.update_booking_status(user_id, "مؤكد")

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "✅ **تم تأكيد حجزك!**\n\n"
                "تم تأكيد موعدك في مركز أمل. ننتظرك! 🌟\n\n"
                "📝 سيتم تذكيرك قبل موعدك بساعة واحدة.\n\n"
                "للاستفسار: 0569509093"
            ),
            parse_mode="Markdown"
        )
        logger.info(f"Confirmation message sent to user {user_id} for booking confirmation.")
    except Exception as e:
        logger.error(f"Failed to send confirmation to user {user_id}: {e}")

    await query.edit_message_text("✅ تم تأكيد الحجز وإرسال إشعار للمريض.", parse_mode="Markdown")

async def admin_set_status(update: Update, context: ContextTypes.DEFAULT_TYPE, new_status: str):
    query = update.callback_query
    await query.answer()
    try:
        user_id = int(query.data.split("_")[-1])
    except Exception:
        await query.edit_message_text("حدث خطأ أثناء تغيير الحالة.")
        return

    db.update_booking_status(user_id, new_status)

    if new_status == "تم التصوير":
        rating_buttons = [
            [InlineKeyboardButton("⭐", callback_data=f"rate_1")],
            [InlineKeyboardButton("⭐⭐", callback_data=f"rate_2")],
            [InlineKeyboardButton("⭐⭐⭐", callback_data=f"rate_3")],
            [InlineKeyboardButton("⭐⭐⭐⭐", callback_data=f"rate_4")],
            [InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data=f"rate_5")]
        ]
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "🌟 **شكراً لزيارتك مركز أمل!**\n\n"
                    "نأمل أن تكون خدمتنا قد نالت رضاك.\n"
                    "من فضلك، خذ لحظة لتقييمنا:"
                ),
                reply_markup=InlineKeyboardMarkup(rating_buttons),
                parse_mode="Markdown"
            )
            logger.info(f"Rating request sent to user {user_id}.")
        except Exception as e:
            logger.error(f"Failed to send rating request to user {user_id}: {e}")

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
    try:
        user_id = int(query.data.split("_")[-1])
    except Exception:
        await query.edit_message_text("حدث خطأ أثناء حذف الحجز.")
        return

    logger.info(f"Admin is deleting booking for user {user_id}.")
    booking = db.get_booking(user_id)
    db.delete_booking(user_id)

    await query.edit_message_text("🗑️ تم الحذف بنجاح.", parse_mode="Markdown")
    logger.info(f"Booking for user {user_id} deleted successfully. Admin notified.")

async def admin_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    stats = db.get_statistics()

    text = (
        "📊 **إحصائيات المركز**\n\n"
        f"📋 إجمالي الحجوزات: {stats['bookings']['total_bookings']}\n"
        f"⏳ قيد الانتظار: {stats['bookings']['pending']}\n"
        f"✅ مؤكدة: {stats['bookings']['confirmed']}\n"
        f"✔️ مكتملة: {stats['bookings']['completed']}\n"
        f"❌ لم يحضر: {stats['bookings']['no_show']}\n\n"
        "**الخدمات الأكثر طلباً:**\n"
    )
    for service in stats['services']:
        text += f"• {service['service']}: {service['count']} حجز\n"

    avg_rating = stats['ratings'].get('avg_rating') if stats.get('ratings') else None
    total_ratings = stats['ratings'].get('total_ratings') if stats.get('ratings') else 0
    if avg_rating:
        text += f"\n⭐ **متوسط التقييم:** {avg_rating:.2f}/5.0\n"
        text += f"📝 **عدد التقييمات:** {total_ratings}"

    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='admin_menu')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def admin_view_ratings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    ratings = db.get_ratings()
    if not ratings:
        text = "لا توجد تقييمات بعد."
    else:
        text = "⭐ **التقييمات:**\n\n"
        for rating in ratings[:50]:
            stars = "⭐" * rating.get('stars', 0)
            name = rating.get('name', 'مجهول')
            fb = rating.get('feedback')
            text += f"{stars} ({rating.get('stars',0)}/5) - {name}\n"
            if fb:
                text += f"💬 {fb}\n"
            text += "\n"

    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='admin_menu')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def admin_waiting_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    waiting_list = waiting_manager.get_waiting_list()
    if not waiting_list:
        text = "📋 **قائمة الانتظار فارغة**"
    else:
        text = "📋 **قائمة الانتظار الحالية:**\n\n"
        for user_id, user_data in waiting_list.items():
            wait_time = datetime.now() - user_data['timestamp']
            text += f"👤 {user_data['name']}\n📞 {user_data['phone']}\n🦷 {user_data['service']}\n⏰ منذ {int(wait_time.total_seconds() / 60)} دقيقة\n\n"
    
    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='admin_menu')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_user_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # إحصائيات بيانات المستخدمين
    total_users = len(user_data_manager.user_preferences)
    frequent_users = sum(1 for data in user_data_manager.user_preferences.values() if data.get('booking_count', 0) > 1)
    
    text = (
        "👥 **إحصائيات المستخدمين**\n\n"
        f"📊 إجمالي المستخدمين: {total_users}\n"
        f"🔄 العملاء الدائمين: {frequent_users}\n"
        f"📈 نسبة العودة: {frequent_users/max(total_users,1)*100:.1f}%\n\n"
        "💡 **ملاحظة:** نظام حفظ البيانات يحسن تجربة المستخدم ويزيد من نسبة العودة"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='admin_menu')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# -----------------------
# ADMIN ACCESS COMMAND
# -----------------------
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ هذه الميزة مخصصة للمشرفين فقط.")
        return
    
    text = "🔐 **لوحة تحكم المشرف**\nاختر إجراءً:"
    keyboard = [
        [InlineKeyboardButton("👁️ عرض جميع الحجوزات", callback_data='admin_view')],
        [InlineKeyboardButton("⏳ الحجوزات المعلقة", callback_data='admin_pending')],
        [InlineKeyboardButton("📊 التقارير والإحصائيات", callback_data='admin_stats')],
        [InlineKeyboardButton("⭐ التقييمات", callback_data='admin_ratings')],
        [InlineKeyboardButton("📋 قائمة الانتظار", callback_data='admin_waiting_list')],
        [InlineKeyboardButton("👥 بيانات المستخدمين", callback_data='admin_user_data')],
        [InlineKeyboardButton("🏠 العودة للقائمة", callback_data='back')],
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# -----------------------
# نظام الحجز المحسن مع حفظ البيانات
# -----------------------
async def book_appointment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_data = user_data_manager.get_user_data(user_id)
    
    if user_data_manager.has_previous_data(user_id):
        # استخدام البيانات المحفوظة
        context.user_data['name'] = user_data['name']
        context.user_data['phone'] = user_data['phone']
        
        keyboard = [
            [InlineKeyboardButton("نعم، استخدام بياناتي", callback_data='use_saved_data')],
            [InlineKeyboardButton("تحديث البيانات", callback_data='update_data')],
        ]
        await query.message.reply_text(
            f"👋 مرحباً بعودتك {user_data['name']}!\n\n"
            "هل تريد استخدام بياناتك المحفوظة؟",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return State.NAME
    else:
        await query.message.reply_text("🖊️ من فضلك، أدخل **اسمك الكامل**: 👤", parse_mode="Markdown")
        return State.NAME

async def use_saved_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_data = user_data_manager.get_user_data(user_id)
    
    # تخطي إدخال الاسم والهاتف
    keyboard = [
        [InlineKeyboardButton("📸 بانورامي", callback_data='service_تصوير بانورامي')],
        [InlineKeyboardButton("🦴 CBCT ثلاثي الأبعاد", callback_data='service_تصوير CBCT ثلاثي الأبعاد')],
        [InlineKeyboardButton("👃 الجيوب الأنفية", callback_data='service_تصوير الجيوب الأنفية')],
        [InlineKeyboardButton("🦷 مفصل الفك", callback_data='service_تصوير مفصل الفك')],
        [InlineKeyboardButton("🩺 غير متأكد", callback_data='service_غير متأكد')],
    ]
    await query.edit_message_text("🔍 ما نوع التصوير المطلوب؟", reply_markup=InlineKeyboardMarkup(keyboard))
    return State.SERVICE

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        # إذا جاء من زر "تحديث البيانات"
        await update.callback_query.message.reply_text("🖊️ من فضلك، أدخل **اسمك الكامل**: 👤", parse_mode="Markdown")
    else:
        context.user_data['name'] = update.message.text.strip()
        await update.message.reply_text("📞 من فضلك، أدخل **رقم جوالك**:", parse_mode="Markdown")
    return State.PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = update.message.text.strip()
    
    # حفظ البيانات للمرة القادمة
    user_data_manager.save_user_data(
        update.effective_user.id,
        context.user_data['name'],
        context.user_data['phone']
    )
    
    keyboard = [
        [InlineKeyboardButton("📸 بانورامي", callback_data='service_تصوير بانورامي')],
        [InlineKeyboardButton("🦴 CBCT ثلاثي الأبعاد", callback_data='service_تصوير CBCT ثلاثي الأبعاد')],
        [InlineKeyboardButton("👃 الجيوب الأنفية", callback_data='service_تصوير الجيوب الأنفية')],
        [InlineKeyboardButton("🦷 مفصل الفك", callback_data='service_تصوير مفصل الفك')],
        [InlineKeyboardButton("🩺 غير متأكد", callback_data='service_غير متأكد')],
    ]
    await update.message.reply_text("🔍 ما نوع التصوير المطلوب؟", reply_markup=InlineKeyboardMarkup(keyboard))
    return State.SERVICE

async def get_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    selected = query.data.replace('service_', '')
    context.user_data['service'] = selected

    available_days = db.get_available_days_for_booking()
    if not available_days:
        # إذا لا توجد أيام متاحة، عرض خيار قائمة الانتظار
        keyboard = [
            [InlineKeyboardButton("نعم، أريد الانتظار", callback_data='join_waiting_list')],
            [InlineKeyboardButton("لا، شكراً", callback_data='back')],
        ]
        await query.edit_message_text(
            "❌ **عذرًا، لا توجد أيام متاحة للحجز حاليًا.**\n\n"
            "هل تريد الانضمام إلى قائمة الانتظار؟ سنخبرك عندما تتوفر أوقات جديدة. 📩",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return State.WAITING_LIST

    now = datetime.now()
    current_weekday = now.weekday()
    weekday_names = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]

    keyboard = []
    for day_name in available_days:
        if day_name not in weekday_names:
            continue
        target_weekday_num = weekday_names.index(day_name)
        days_ahead = target_weekday_num - current_weekday
        if days_ahead < 0:
            days_ahead += 7
        target_date = (now + timedelta(days=days_ahead)).date()
        formatted_date = target_date.strftime("%d/%m/%Y")
        button_text = f"{formatted_date} يوم {day_name}"
        callback_data = f"day_{formatted_date}_{day_name}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    await query.edit_message_text("📅 **اختر اليوم والتاريخ المناسب لك:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return State.DAY

async def get_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_", 2)
    if len(parts) < 3 or parts[0] != "day":
        logger.error(f"Unexpected callback data format: {query.data}")
        await query.edit_message_text("❌ **حدث خطأ أثناء اختيار اليوم. يرجى المحاولة مرة أخرى.**")
        return ConversationHandler.END
    selected_date_str = parts[1]
    selected_day_name = parts[2]

    context.user_data['day'] = selected_day_name
    context.user_data['selected_date_str'] = selected_date_str

    available_time_slots = db.get_available_time_slots_for_day(context.user_data['day'])
    if not available_time_slots:
        await query.edit_message_text(f"❌ **عذرًا، لا توجد أوقات متاحة لليوم {context.user_data['day']}**.\nيرجى اختيار يوم آخر.")
        return await get_service(update, context)

    keyboard = []
    for slot in available_time_slots:
        keyboard.append([InlineKeyboardButton(f"✅ {slot}", callback_data=f"time_{slot}")])

    await query.edit_message_text(
        f"⏰ **اختر الوقت المتاح في يوم {context.user_data['day']} ({selected_date_str}):**\n\n"
        "✅ = متاح",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return State.TIME_SLOT

async def get_time_slot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    time_slot = query.data.replace("time_", "")
    context.user_data['time'] = time_slot
    keyboard = [
        [InlineKeyboardButton("⏰ عادي", callback_data='type_normal')],
        [InlineKeyboardButton("⚠️ طارئ", callback_data='type_emergency')],
    ]
    await query.edit_message_text("🚨 هل هذا موعد **عادي** أم **طارئ**؟", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return State.EMERGENCY

async def confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    emergency_status = "طارئ" if query.data == 'type_emergency' else "عادي"
    current_date = context.user_data.get('selected_date_str', datetime.now().strftime("%d/%m/%Y"))
    user_id = update.effective_user.id

    appointment_datetime = None
    try:
        if context.user_data.get('selected_date_str') and context.user_data.get('time'):
            selected_date_obj = datetime.strptime(context.user_data['selected_date_str'], "%d/%m/%Y")
            time_str = context.user_data['time']
            hour = int(time_str.split(":")[0])
            if "مساءً" in time_str and hour != 12:
                hour += 12
            elif "صباحاً" in time_str and hour == 12:
                hour = 0
            appointment_datetime = selected_date_obj.replace(hour=hour, minute=0, second=0, microsecond=0)
    except Exception as e:
        logger.error(f"Error parsing appointment datetime: {e}")

    db.create_booking(
        user_id=user_id,
        name=context.user_data.get('name', 'مجهول'),
        phone=context.user_data.get('phone', '-'),
        service=context.user_data.get('service', '-'),
        day=context.user_data.get('day', '-'),
        time=context.user_data.get('time', '-'),
        date=current_date,
        booking_type=emergency_status,
        appointment_datetime=appointment_datetime
    )

    summary = (
        "🎊 **تم استلام طلب حجزك بنجاح!**\n\n"
        f"👤 الاسم: {context.user_data.get('name','-')}\n"
        f"📞 الجوال: {context.user_data.get('phone','-')}\n"
        f"🦷 الخدمة: {context.user_data.get('service','-')}\n"
        f"📅 اليوم: {context.user_data.get('day','-')}\n"
        f"⏰ الوقت: {context.user_data.get('time','-')}\n"
        f"📆 التاريخ: {current_date}\n"
        f"🚨 النوع: {emergency_status}\n\n"
        "⏳ حجزك الآن **قيد المراجعة**\n"
        "سيتم التواصل معك قريباً لتأكيد الموعد.\n\n"
        "شكرًا لثقتكم بنا! 🌸"
    )
    await query.message.reply_text(summary, parse_mode="Markdown")

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=(
                    f"🔔 **حجز جديد {emergency_status}!**\n\n"
                    f"👤 {context.user_data.get('name','-')}\n"
                    f"📞 {context.user_data.get('phone','-')}\n"
                    f"🦷 {context.user_data.get('service','-')}\n"
                    f"📅 {context.user_data.get('day','-')} - {context.user_data.get('time','-')}\n"
                    f"📆 {current_date}\n"
                    f"🚨 {emergency_status}"
                ),
                parse_mode="Markdown"
            )
            logger.info(f"New booking notification sent to admin {admin_id}.")
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")

    for k in ['name','phone','service','day','time','selected_date_str']:
        context.user_data.pop(k, None)

    return ConversationHandler.END

async def join_waiting_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    waiting_manager.add_to_waiting_list(user_id, context.user_data)
    
    await query.edit_message_text(
        "✅ **تم إضافتك إلى قائمة الانتظار!**\n\n"
        f"عزيزي/عزيزتي {context.user_data.get('name')}\n"
        f"🦷 الخدمة: {context.user_data.get('service')}\n\n"
        "سنقوم بإشعارك فور توفر أوقات جديدة. 📩\n\n"
        "شكراً لصبرك وثقتك بمركز أمل! 🌸"
    )
    
    # تنظيف البيانات
    for k in ['name','phone','service']:
        context.user_data.pop(k, None)
    
    return ConversationHandler.END

# -----------------------
# RATING FLOW
# -----------------------
async def handle_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        stars = int(query.data.split("_")[1])
    except Exception:
        logger.error(f"Invalid rating callback data: {query.data}")
        await query.edit_message_text("❌ حدث خطأ في التقييم. الرجاء المحاولة لاحقاً.")
        return ConversationHandler.END

    user_id = update.effective_user.id
    context.user_data['rating_stars'] = stars

    if stars < 4:
        await query.edit_message_text(
            f"❌ **تم تقييمك بـ {'⭐' * stars}.**\n\n"
            "نأسف لسماع أن تجربتك لم تكن مرضية.\n"
            "هل يمكنك مشاركتنا اقتراح تعديل أو ملاحظة لتحسين خدمتنا؟\n\n"
            "من فضلك، اكتب اقتراحك أو ملاحظتك:",
            parse_mode="Markdown"
        )
        return State.RATING_FEEDBACK

    db.save_rating(user_id, stars, None)
    if stars == 5:
        await query.edit_message_text(
            "🌟 **5 نجوم! شكرًا جزيلاً!**\n\n"
            "نُقدّر اختيارك وثقتَك بمركز أمل.\n"
            "نأمل أن تكون قد استمتعت بتجربة ممتازة معنا. ❤️",
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text(
            f"⭐ **تم تقييمك بـ {'⭐' * stars}.**\n\n"
            "شكرًا لتقييمك! نحن نسعى دائمًا للتحسين.",
            parse_mode="Markdown"
        )

    for admin_id in ADMIN_IDS:
        try:
            booking = db.get_booking(user_id)
            name = booking['name'] if booking else update.effective_user.full_name or "مجهول"
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"⭐ **تقييم جديد!**\n\n👤 {name}\n⭐ {stars}/5",
                parse_mode="Markdown"
            )
            logger.info(f"Rating notification sent to admin {admin_id} for user {user_id}, {stars} stars.")
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id} about rating: {e}")

    context.user_data.pop('rating_stars', None)
    return ConversationHandler.END

async def get_rating_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    feedback = update.message.text.strip()
    stars = context.user_data.get('rating_stars', 3)
    user_id = update.effective_user.id

    db.save_rating(user_id, stars, feedback)
    logger.info(f"Rating with feedback saved for user {user_id}, {stars} stars: {feedback}")

    await update.message.reply_text(
        f"❌ **تم تقييمك بـ {'⭐' * stars}.**\n\n"
        "شكرًا لك! 🙏\n\n"
        "ملاحظاتك مهمة جداً لنا وسنعمل على تحسين خدمتنا.\n"
        "نتمنى أن نكون أفضل في المرة القادمة! ❤️",
        parse_mode="Markdown"
    )

    for admin_id in ADMIN_IDS:
        try:
            booking = db.get_booking(user_id)
            name = booking['name'] if booking else update.effective_user.full_name or "مجهول"
            await context.bot.send_message(
                chat_id=admin_id,
                text=(
                    f"⚠️ **تقرير تقييم منخفض مع ملاحظات**\n\n"
                    f"👤 {name}\n"
                    f"⭐ {stars}/5\n\n"
                    f"💬 **الملاحظات:**\n{feedback}"
                ),
                parse_mode="Markdown"
            )
            logger.info(f"Rating feedback sent to admin {admin_id} for user {user_id}, {stars} stars: {feedback}")
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id} about feedback: {e}")

    context.user_data.pop('rating_stars', None)
    return ConversationHandler.END

# -----------------------
# FAQ SYSTEM
# -----------------------
async def faq_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = "❓ **الأسئلة الشائعة**\n\nاختر سؤالاً للاطلاع على إجابته:"
    await query.edit_message_text(text, reply_markup=faq_manager.get_faq_keyboard(), parse_mode="Markdown")
    return State.FAQ

async def show_faq_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    faq_key = query.data.replace("faq_", "")
    answer = faq_manager.get_faq_answer(faq_key)
    
    keyboard = [[InlineKeyboardButton("🔙 رجوع للأسئلة", callback_data='faq_menu')]]
    await query.edit_message_text(answer, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return State.FAQ

# -----------------------
# نظام تفضيلات المستخدم
# -----------------------
async def user_preferences_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    preferences = notification_manager.get_user_preferences(user_id)
    
    keyboard = [
        [InlineKeyboardButton(
            f"{'✅' if preferences['morning_notifications'] else '❌'} إشعارات الصباح", 
            callback_data='toggle_morning'
        )],
        [InlineKeyboardButton(
            f"{'✅' if preferences['evening_notifications'] else '❌'} إشعارات المساء", 
            callback_data='toggle_evening'
        )],
        [InlineKeyboardButton(
            f"{'✅' if preferences['weather_alerts'] else '❌'} تنبيهات الطقس", 
            callback_data='toggle_weather'
        )],
        [InlineKeyboardButton(
            f"{'✅' if preferences['promotions'] else '❌'} العروض والتخفيضات", 
            callback_data='toggle_promotions'
        )],
        [InlineKeyboardButton("🏠 العودة للقائمة", callback_data='back')],
    ]
    
    await query.edit_message_text(
        "⚙️ **تفضيلات الإشعارات**\n\n"
        "اختر أنواع الإشعارات التي تريد استقبالها:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return State.USER_PREFERENCES

async def toggle_preference(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    preference_type = query.data.replace('toggle_', '')
    preferences = notification_manager.get_user_preferences(user_id)
    
    preferences[preference_type] = not preferences[preference_type]
    notification_manager.set_user_preferences(user_id, preferences)
    
    return await user_preferences_menu(update, context)

# -----------------------
# نظام الإشعارات الذكية
# -----------------------
async def send_weather_alerts(context: ContextTypes.DEFAULT_TYPE):
    """إرسال تنبيهات الطقس للمستخدمين"""
    weather_alert = await weather_manager.get_weather_alert()
    if weather_alert:
        # الحصول على الحجوزات القادمة خلال 24 ساعة
        upcoming_bookings = db.get_confirmed_bookings_for_reminders()
        
        for booking in upcoming_bookings:
            user_prefs = notification_manager.get_user_preferences(booking['user_id'])
            if user_prefs.get('weather_alerts', True):
                try:
                    await context.bot.send_message(
                        chat_id=booking['user_id'],
                        text=weather_alert,
                        parse_mode="Markdown"
                    )
                    logger.info(f"Weather alert sent to user {booking['user_id']}")
                except Exception as e:
                    logger.error(f"Failed to send weather alert to user {booking['user_id']}: {e}")

async def notify_waiting_list_updates(context: ContextTypes.DEFAULT_TYPE):
    """التحقق من توفر أوقات جديدة وإشعار قائمة الانتظار"""
    available_days = db.get_available_days_for_booking()
    if available_days:
        for day_name in available_days:
            available_slots = db.get_available_time_slots_for_day(day_name)
            if available_slots:
                await waiting_manager.notify_waiting_users(context, day_name, available_slots)

async def send_reminders(context: ContextTypes.DEFAULT_TYPE):
    """إرسال تذكيرات المواعيد"""
    bookings = db.get_confirmed_bookings_for_reminders()
    for booking in bookings:
        try:
            await context.bot.send_message(
                chat_id=booking['user_id'],
                text=(
                    f"🔔 **تذكير بموعدك!**\n\n"
                    f"عزيزي/عزيزتي {booking['name']}\n\n"
                    f"موعدك في مركز أمل خلال ساعة:\n"
                    f"⏰ {booking['time']}\n"
                    f"🦷 {booking['service']}\n\n"
                    f"📍 نابلس - عسكر القديم - مقابل مخبز أبو عبده\n"
                    f"📞 للاستفسار: 0569509093\n\n"
                    f"ننتظرك! 🌟"
                ),
                parse_mode="Markdown"
            )
            logger.info(f"Reminder sent to user {booking['user_id']}")
        except Exception as e:
            logger.error(f"Failed to send reminder to user {booking['user_id']}: {e}")

# -----------------------
# General / UI / Misc handlers
# -----------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == 'book':
        return await book_appointment(update, context)
    elif data == 'admin_menu':
        return await admin_menu(update, context)
    elif data == 'admin_view':
        return await admin_view_bookings(update, context)
    elif data == 'admin_pending':
        return await admin_pending_bookings(update, context)
    elif data == 'admin_stats':
        return await admin_statistics(update, context)
    elif data == 'admin_ratings':
        return await admin_view_ratings(update, context)
    elif data == 'admin_waiting_list':
        return await admin_waiting_list(update, context)
    elif data == 'admin_user_data':
        return await admin_user_data(update, context)
    elif data.startswith('admin_edit_'):
        return await admin_edit_booking(update, context)
    elif data.startswith('admin_confirm_delete_'):
        return await admin_confirm_delete(update, context)
    elif data.startswith('admin_delete_'):
        return await admin_delete_booking(update, context)
    elif data.startswith('admin_confirm_'):
        return await admin_confirm_booking(update, context)
    elif data.startswith('admin_set_done_'):
        return await admin_set_status(update, context, "تم التصوير")
    elif data.startswith('admin_set_absent_'):
        return await admin_set_status(update, context, "لم يحضر")
    elif data.startswith('service_'):
        return await get_service(update, context)
    elif data.startswith('type_'):
        return await confirm_booking(update, context)
    elif data.startswith('rate_'):
        return await handle_rating(update, context)
    elif data == 'faq_menu':
        return await faq_menu(update, context)
    elif data.startswith('faq_'):
        return await show_faq_answer(update, context)
    elif data == 'user_preferences':
        return await user_preferences_menu(update, context)
    elif data.startswith('toggle_'):
        return await toggle_preference(update, context)
    elif data == 'use_saved_data':
        return await use_saved_data(update, context)
    elif data == 'update_data':
        return await get_name(update, context)
    elif data == 'join_waiting_list':
        return await join_waiting_list(update, context)
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
            "✨ نتائج موثوقة يعتمد عليها الأطباء عالمياً\n\n"
            "📍 **الموقع:** نابلس - عسكر القديم - الشارع الرئيسي، مقابل مخبز أبو عبده\n"
            "📞 **للحجز:** [0569509093](tel:+970569509093)"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 العودة للقائمة", callback_data='back')]]), parse_mode="Markdown")
        return ConversationHandler.END
    elif data == 'video':
        text = (
            "🎥 **شاهد مركز أمل**\n\n"
            "تفضل بمشاهدة قناتنا على اليوتيوب للتعرف على المركز وخدماتنا:\n\n"
            "🔗 [قناة مركز أمل على اليوتيوب](https://youtube.com/@amal-xray-center)"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 العودة للقائمة", callback_data='back')]]), parse_mode="Markdown", disable_web_page_preview=False)
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
            "👩‍⚕️ **للسيدات الحوامل:**\n"
            "• يُرجى إخبار الفني قبل التصوير\n\n"
            "📞 **لأي استفسار:** 0569509093"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 العودة للقائمة", callback_data='back')]]), parse_mode="Markdown")
        return ConversationHandler.END
    elif data == 'location':
        text = (
            "📍 **موقع مركز أمل**\n\n"
            "**العنوان:**\n"
            "نابلس - عسكر القديم - الشارع الرئيسي\n"
            "مقابل مخبز أبو عبده\n\n"
            "🕘 **ساعات العمل:**\n"
            "من 9:00 صباحاً - 8:00 مساءً\n"
            "جميع أيام الأسبوع\n\n"
            "📞 **للحجز والاستفسار:**\n"
            "[0569509093](tel:+970569509093)\n\n"
            "🗺️ **خريطة الموقع:**\n"
            "[افتح الموقع في خرائط Google](https://www.google.com/maps)"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 العودة للقائمة", callback_data='back')]]), parse_mode="Markdown")
        return ConversationHandler.END
    elif data == 'my_bookings':
        user_id = update.effective_user.id
        booking = db.get_booking(user_id)

        if not booking:
            text = "**لا توجد حجوزات**\n\nليس لديك أي حجوزات حالياً.\nيمكنك حجز موعد جديد من القائمة الرئيسية."
        else:
            status_emoji = {"قيد الانتظار": "⏳", "مؤكد": "✅", "تم التصوير": "✔️", "لم يحضر": "❌"}
            status = booking.get('status', 'غير محدد')
            emoji = status_emoji.get(status, "📋")
            text = (
                f"{emoji} **حجزك الحالي**\n\n"
                f"👤 الاسم: {booking.get('name','-')}\n"
                f"📞 الجوال: {booking.get('phone','-')}\n"
                f"🦷 نوع التصوير: {booking.get('service','-')}\n"
                f"📅 اليوم: {booking.get('day','-')}\n"
                f"⏰ الوقت: {booking.get('time','-')}\n"
                f"📆 التاريخ: {booking.get('date','-')}\n"
                f"🚨 النوع: {booking.get('type','-')}\n"
                f"📊 الحالة: **{status}**\n\n"
            )
            if status == "قيد الانتظار":
                text += "⏳ سيتم التواصل معك قريباً لتأكيد الموعد."
            elif status == "مؤكد":
                text += "✅ موعدك مؤكد! ننتظرك.\n📝 سيتم تذكيرك قبل موعدك بساعة."
            elif status == "تم التصوير":
                text += "✔️ تم إنجاز التصوير بنجاح. شكراً لزيارتك!"

        keyboard = []
        if booking and booking.get('status') in ['قيد الانتظار', 'مؤكد']:
            keyboard.append([InlineKeyboardButton("🗑️ إلغاء الحجز", callback_data='cancel_my_booking')])
        keyboard.append([InlineKeyboardButton("🏠 العودة للقائمة", callback_data='back')])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return ConversationHandler.END
    elif data == 'cancel_my_booking':
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
        user_id = update.effective_user.id
        db.delete_booking(user_id)
        text = "✅ **تم إلغاء حجزك بنجاح**\n\nيمكنك حجز موعد جديد في أي وقت."
        keyboard = [[InlineKeyboardButton("🏠 العودة للقائمة", callback_data='back')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return ConversationHandler.END
    elif data == 'back':
        theme = theme_manager.get_theme_config()
        await query.edit_message_text(theme["welcome_message"], reply_markup=main_menu_keyboard(), parse_mode="Markdown")
        return ConversationHandler.END
    else:
        await query.edit_message_text("جارٍ التحميل...", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 العودة للقائمة", callback_data='back')]]), parse_mode="Markdown")
        return ConversationHandler.END

# -----------------------
# Cancel handler util
# -----------------------
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("تم الإلغاء.")
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("تم الإلغاء.")
    return ConversationHandler.END

# -----------------------
# Main: register handlers and run
# -----------------------
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Job queue للمهام المجدولة
    job_queue = application.job_queue
    
    # التذكيرات الأساسية (كل 5 دقائق)
    job_queue.run_repeating(send_reminders, interval=300, first=10)
    
    # تنبيهات الطقس (كل 6 ساعات)
    job_queue.run_repeating(send_weather_alerts, interval=21600, first=60)
    
    # تحديث قائمة الانتظار (كل 30 دقيقة)
    job_queue.run_repeating(notify_waiting_list_updates, interval=1800, first=120)

    # ConversationHandler للحجز الأساسي
    booking_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(book_appointment, pattern='^book$')],
        states={
            State.NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_name),
                CallbackQueryHandler(use_saved_data, pattern='^use_saved_data$'),
                CallbackQueryHandler(get_name, pattern='^update_data$')
            ],
            State.PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            State.SERVICE: [CallbackQueryHandler(get_service, pattern='^service_')],
            State.DAY: [CallbackQueryHandler(get_day, pattern='^day_')],
            State.TIME_SLOT: [CallbackQueryHandler(get_time_slot, pattern='^time_')],
            State.EMERGENCY: [CallbackQueryHandler(confirm_booking, pattern='^type_')],
            State.WAITING_LIST: [CallbackQueryHandler(join_waiting_list, pattern='^join_waiting_list$')],
        },
        fallbacks=[CommandHandler('cancel', cancel_command)],
    )

    # ConversationHandler للتقييم
    rating_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_rating, pattern='^rate_\\d$')],
        states={
            State.RATING_FEEDBACK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_rating_feedback)],
        },
        fallbacks=[CommandHandler('cancel', cancel_command)],
    )

    # ConversationHandler للأسئلة الشائعة
    faq_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(faq_menu, pattern='^faq_menu$')],
        states={
            State.FAQ: [CallbackQueryHandler(show_faq_answer, pattern='^faq_')],
        },
        fallbacks=[CommandHandler('cancel', cancel_command)],
    )

    # ConversationHandler لتفضيلات المستخدم
    preferences_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(user_preferences_menu, pattern='^user_preferences$')],
        states={
            State.USER_PREFERENCES: [CallbackQueryHandler(toggle_preference, pattern='^toggle_')],
        },
        fallbacks=[CommandHandler('cancel', cancel_command)],
    )

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(booking_conv)
    application.add_handler(rating_conv)
    application.add_handler(faq_conv)
    application.add_handler(preferences_conv)

    # Generic CallbackQuery router for buttons
    application.add_handler(CallbackQueryHandler(button_handler))

    # Start polling
    logger.info("Starting enhanced bot with all features...")
    application.run_polling()

if __name__ == "__main__":
    main()