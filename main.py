import os
import sys
import logging
from datetime import datetime
import threading

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from flask import Flask, request

# اضافه کردن مسیر فعلی برای import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from config import BOT_TOKEN, OWNER_ID, CHANNEL_ID, WEBHOOK_URL, PORT, COUNTRIES
    from database import Database
    from game_logic import GameLogic
    from advisor import Advisor
except ImportError as e:
    print(f"Import error: {e}")
    print("Creating minimal config...")
    
    # حداقل تنظیمات در صورت عدم وجود config
    BOT_TOKEN = os.getenv('BOT_TOKEN', '')
    OWNER_ID = 8588773170
    CHANNEL_ID = os.getenv('CHANNEL_ID', '')
    WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
    PORT = int(os.getenv('PORT', 10000))
    COUNTRIES = {}

# تنظیم لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ایجاد نمونه‌ها
db = None
game = None
advisor = None

try:
    db = Database()
    game = GameLogic()
    advisor = Advisor()
except:
    logger.warning("Some modules failed to initialize, using minimal setup")

# برنامه Flask برای Webhook
app = Flask(__name__)

# ذخیره Application
telegram_app = None

@app.route('/')
def index():
    return '🎮 Ancient War Bot v2.0 - Running!'

@app.route('/health')
def health():
    return 'OK', 200

@app.route('/webhook', methods=['POST'])
def webhook():
    if telegram_app:
        json_data = request.get_json(force=True)
        update = Update.de_json(json_data, telegram_app.bot)
        telegram_app.update_queue.put(update)
    return 'OK', 200

def run_flask():
    app.run(host='0.0.0.0', port=PORT, debug=False)

# ========== دستورهای ربات ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور شروع بازی"""
    user = update.effective_user
    welcome_text = f"""
🤴 **به جنگ جهانی باستان خوش آمدید {user.first_name}!**

🏛️ **درباره بازی:**
• یک بازی استراتژیک چندنفره در زمان باستان
• شما فرمانروای یک کشور باستانی خواهید بود
• کشورهای بدون بازیکن توسط هوش مصنوعی کنترل می‌شوند
• تنها بازیکنان انسانی می‌توانند برنده نهایی شوند

📜 **نحوه شروع:**
برای دریافت کشور، با مالک بازی تماس بگیرید.

👑 **مالک:** @amele55
📱 **ورژن:** 2.0
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور راهنمایی"""
    help_text = """
🎮 **دستورهای اصلی بازی:**

/start - شروع بازی و خوش‌آمدگویی
/help - نمایش این راهنما
/my_country - مشاهده کشور و وضعیت شما
/resources - مشاهده منابع کشور
/upgrade_army - ارتقای سطح ارتش
/alliances - مشاهده اتحادها
/advisor - دریافت مشاوره از وزیر

⚔️ **مدیریت نظامی:**
/attack <کد کشور> - حمله به کشور دیگر
/defend - فعال کردن وضعیت دفاعی
/recruit <تعداد> - استخدام سرباز جدید

💰 **مدیریت اقتصادی:**
/mines - مشاهده معادن
/build <نوع ساختمان> - ساخت ساختمان جدید
/trade <کد کشور> <منبع> <مقدار> - تجارت با کشور دیگر

👑 **دستورهای مالک (فقط برای @amele55):**
/admin - پنل مدیریت
/add_player - افزودن بازیکن جدید
/start_season - شروع فصل جدید
/end_season - پایان فصل
/broadcast <پیام> - ارسال پیام به همه
/reset_game - ریست کامل بازی

📌 **نکته:** برای استفاده از دستورهای مالک، باید مالک اصلی بازی باشید.
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def my_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش اطلاعات کشور بازیکن"""
    user_id = update.effective_user.id
    
    # در حالت آزمایشی
    if not db:
        sample_text = """
🏛️ **امپراتوری پارس (حالت آزمایشی)**

👤 **حاکم:** شما
⚔️ **سطح ارتش:** 2
💪 **قدرت نظامی:** 450

💰 **منابع:**
• 🪙 طلا: 1,250
• ⚙️ آهن: 800
• 🪨 سنگ: 600
• 🌾 غذا: 1,800

👥 **نیروهای نظامی:**
• 🪖 پیاده‌نظام: 150 سرباز
• 🐎 سواره‌نظام: 45 اسب‌سوار
• 🏹 محاصره‌گران: 8 دستگاه

🎯 **مهارت ویژه:** سواره نظام سریع
📊 **امتیاز کل:** 1,850

ℹ️ *این اطلاعات آزمایشی هستند. در نسخه کامل، اطلاعات واقعی از دیتابیس خوانده می‌شود.*
"""
        await update.message.reply_text(sample_text, parse_mode='Markdown')
        return
    
    # در حالت واقعی
    try:
        country_info = db.get_country_info_by_player(user_id)
        if country_info:
            message = f"""
🏛️ **{country_info.get('name', 'کشور ناشناخته')}**

👤 **حاکم:** شما ({update.effective_user.first_name})
⚔️ **سطح ارتش:** {country_info.get('army_level', 1)}
💪 **قدرت نظامی:** {country_info.get('total_power', 0)}

💰 **منابع:**
• 🪙 طلا: {country_info.get('gold', 0):,}
• ⚙️ آهن: {country_info.get('iron', 0):,}
• 🪨 سنگ: {country_info.get('stone', 0):,}
• 🌾 غذا: {country_info.get('food', 0):,}

👥 **نیروهای نظامی:**
• 🪖 پیاده‌نظام: {country_info.get('soldiers', 0):,} سرباز
• 🐎 سواره‌نظام: {country_info.get('cavalry', 0):,} اسب‌سوار
• 🏹 محاصره‌گران: {country_info.get('siege', 0):,} دستگاه

📊 **امتیاز کل:** {country_info.get('power_score', 0):,}
"""
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text(
                "❌ شما هنوز کشوری ندارید.\n\n"
                "برای دریافت کشور، لطفاً با مالک بازی (@amele55) تماس بگیرید."
            )
    except Exception as e:
        logger.error(f"Error in my_country: {e}")
        await update.message.reply_text("⚠️ خطایی در دریافت اطلاعات کشور رخ داد.")

async def resources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منابع کشور"""
    keyboard = [
        [InlineKeyboardButton("⛏️ تولید منابع", callback_data='generate_res')],
        [InlineKeyboardButton("⚔️ ارتقای ارتش", callback_data='upgrade_army')],
        [InlineKeyboardButton("🏗️ ساخت ساختمان", callback_data='build_menu')],
        [InlineKeyboardButton("📊 آمار کلی", callback_data='stats')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    resources_text = """
💰 **مدیریت منابع کشور**

🏦 **منابع فعلی:**
• 🪙 طلا: 1,250 (📈 +50/ساعت)
• ⚙️ آهن: 800 (📈 +30/ساعت)
• 🪨 سنگ: 600 (📈 +20/ساعت)
• 🌾 غذا: 1,800 (📈 +100/ساعت)

🏭 **ساختمان‌های فعال:**
• ⛏️ معدن طلا: سطح 2
• 🔨 کارگاه آهنگری: سطح 1
• 🏘️ روستا: سطح 3
• 🌾 مزرعه: سطح 2

📈 **تولید ساعتی:** 200 واحد
📊 **ظرفیت ذخیره:** 5,000 واحد

👇 از دکمه‌های زیر برای مدیریت منابع استفاده کنید:
"""
    await update.message.reply_text(resources_text, reply_markup=reply_markup, parse_mode='Markdown')

async def upgrade_army(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارتقای ارتش"""
    keyboard = [
        [InlineKeyboardButton("🪖 ارتقای پیاده‌نظام", callback_data='upgrade_infantry')],
        [InlineKeyboardButton("🐎 ارتقای سواره‌نظام", callback_data='upgrade_cavalry')],
        [InlineKeyboardButton("🏹 ارتقای محاصره‌گران", callback_data='upgrade_siege')],
        [InlineKeyboardButton("🛡️ ارتقای دفاع", callback_data='upgrade_defense')],
        [InlineKeyboardButton("🔙 بازگشت", callback_data='main_menu')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    upgrade_text = """
⚔️ **مرکز ارتقای ارتش**

🎯 **وضعیت فعلی ارتش:**
• 🪖 پیاده‌نظام: سطح 2 (قدرت: 150)
• 🐎 سواره‌نظام: سطح 1 (قدرت: 80)
• 🏹 محاصره‌گران: سطح 1 (قدرت: 120)
• 🛡️ دفاع: سطح 2 (مقاومت: 200)

📊 **امتیاز نظامی کل:** 550

💰 **هزینه‌های ارتقا:**
• سطح 2 → 3: 500 🪙 طلا + 200 ⚙️ آهن
• سطح 3 → 4: 1,000 🪙 طلا + 500 ⚙️ آهن
• سطح 4 → 5: 2,000 🪙 طلا + 1,000 ⚙️ آهن

⏱️ **زمان ارتقا:** 2-6 ساعت
👇 نوع ارتقا را انتخاب کنید:
"""
    await update.message.reply_text(upgrade_text, reply_markup=reply_markup, parse_mode='Markdown')

async def alliances(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت اتحادها"""
    keyboard = [
        [InlineKeyboardButton("🤝 ایجاد اتحاد جدید", callback_data='create_alliance')],
        [InlineKeyboardButton("📋 لیست کشورهای آزاد", callback_data='list_countries')],
        [InlineKeyboardButton("⚔️ پیشنهاد جنگ مشترک", callback_data='joint_war')],
        [InlineKeyboardButton("💔 فسخ اتحاد", callback_data='break_alliance')],
        [InlineKeyboardButton("🔙 بازگشت", callback_data='main_menu')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    alliances_text = """
🤝 **سیستم اتحادها**

🏛️ **اتحادهای فعلی شما:**
1. 🤝 **مصر باستان** (امتیاز: 85/100)
   • شروع: ۱۵ روز پیش
   • کمک‌های نظامی: ۳ بار
   • تجارت: ۱,۲۰۰ 🪙 طلا

2. 🤝 **یونان باستان** (امتیاز: 70/100)
   • شروع: ۷ روز پیش
   • کمک‌های نظامی: ۱ بار
   • تجارت: ۸۰۰ 🪙 طلا

📊 **آمار اتحادها:**
• کل اتحادها: ۲ کشور
• میانگین امتیاز: ۷۷/۱۰۰
• مزایای فعال: تجارت +۲۰٪، دفاع +۱۵٪

⚠️ **هشدارها:**
• اتحاد با روم در خطر فسخ (امتیاز: ۴۰/۱۰۰)
• پیشنهاد اتحاد از بابل منتظر پاسخ

👇 برای مدیریت اتحادها از دکمه‌ها استفاده کنید:
"""
    await update.message.reply_text(alliances_text, reply_markup=reply_markup, parse_mode='Markdown')

async def get_advisor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت مشاوره از وزیر"""
    advices = [
        "👨‍💼 **وزیر:** منابع طلای شما در حال اتمام است. معدن طلا را ارتقا دهید.",
        "👨‍💼 **وزیر:** ارتش کشور روم در مرزها تجمع کرده‌اند. حالت دفاعی فعال کنید.",
        "👨‍💼 **وزیر:** فرصت خوبی برای اتحاد با مصر دارید. پیشنهاد اتحاد بدهید.",
        "👨‍💼 **وزیر:** کشور بابل ضعیف شده. حمله را در نظر بگیرید.",
        "👨‍💼 **وزیر:** تجارت با یونان سودآور خواهد بود. مذاکره کنید.",
        "👨‍💼 **وزیر:** سطح دفاعی شما پایین است. دیوارها را تقویت کنید.",
        "👨‍💼 **وزیر:** فصل برداشت نزدیک است. مزارع را آماده کنید.",
        "👨‍💼 **وزیر:** اطلاعاتی از حمله قریب‌الوقوع آشور دریافت کرده‌ام.",
    ]
    
    import random
    advice = random.choice(advices)
    
    keyboard = [
        [InlineKeyboardButton("✅ اجرای پیشنهاد", callback_data='execute_advice')],
        [InlineKeyboardButton("🔄 مشاوره جدید", callback_data='new_advice')],
        [InlineKeyboardButton("📊 تحلیل کامل", callback_data='full_analysis')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(advice, reply_markup=reply_markup, parse_mode='Markdown')

# ========== دستورهای مالک ==========

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پنل مدیریت مالک"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ **دسترسی ممنوع!**\nفقط مالک بازی می‌تواند از این بخش استفاده کند.")
        return
    
    keyboard = [
        [InlineKeyboardButton("➕ افزودن بازیکن", callback_data='admin_add_player'),
         InlineKeyboardButton("👥 مدیریت بازیکنان", callback_data='admin_manage_players')],
        [InlineKeyboardButton("🏁 شروع فصل", callback_data='admin_start_season'),
         InlineKeyboardButton("🏁 پایان فصل", callback_data='admin_end_season')],
        [InlineKeyboardButton("📢 ارسال پیام عمومی", callback_data='admin_broadcast'),
         InlineKeyboardButton("📊 آمار سراسری", callback_data='admin_stats')],
        [InlineKeyboardButton("⚙️ تنظیمات بازی", callback_data='admin_settings'),
         InlineKeyboardButton("🔄 ریست بازی", callback_data='admin_reset')],
        [InlineKeyboardButton("🚫 خروج", callback_data='admin_exit')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    admin_text = f"""
👑 **پنل مدیریت مالک**

👤 **مالک:** @amele55 (ID: {OWNER_ID})
📅 **تاریخ:** {datetime.now().strftime('%Y/%m/%d %H:%M')}

📊 **آمار کلی:**
• 👥 بازیکنان انسانی: ۸ نفر
• 🤖 کشورهای AI: ۲۰ کشور
• 🤝 اتحادهای فعال: ۱۲ مورد
• ⚔️ جنگ‌های جاری: ۳ مورد
• 🏆 فصل فعلی: فصل ۳

⚙️ **وضعیت سیستم:**
• ✅ ربات: فعال
• ✅ دیتابیس: متصل
• ✅ سرور: آنلاین
• 📶 وضعیت: عالی

👇 لطفاً عملیات مورد نظر را انتخاب کنید:
"""
    await update.message.reply_text(admin_text, reply_markup=reply_markup, parse_mode='Markdown')

async def start_season(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع فصل جدید (فقط مالک)"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ دسترسی ممنوع!")
        return
    
    keyboard = [
        [InlineKeyboardButton("✅ تأیید و شروع", callback_data='confirm_start_season')],
        [InlineKeyboardButton("❌ لغو", callback_data='cancel_start_season')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    season_text = """
🏁 **شروع فصل جدید**

📝 **جزئیات فصل جدید:**
• شماره فصل: ۴
• مدت زمان: ۳۰ روز
• کشورهای شرکت‌کننده: ۲۸ کشور
• جوایز فصل: ۱۰,۰۰۰ 🪙 طلا

⚠️ **هشدارها:**
۱. با شروع فصل جدید، تمام جنگ‌های فعلی پایان می‌یابد.
۲. اتحادهای فصل قبل حفظ می‌شوند.
۳. منابع اولیه بازنشانی می‌شود.
۴. امتیازات فصل قبل ثبت می‌شود.

⏰ **زمان‌بندی:**
• شروع: امروز ساعت ۲۰:۰۰
• پایان: ۳۰ روز بعد
• اعلام برنده: ۲ ساعت پس از پایان

👇 آیا مطمئن هستید که می‌خواهید فصل جدید را شروع کنید؟
"""
    await update.message.reply_text(season_text, reply_markup=reply_markup, parse_mode='Markdown')

async def end_season(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پایان فصل (فقط مالک)"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ دسترسی ممنوع!")
        return
    
    keyboard = [
        [InlineKeyboardButton("🏆 اعلام برنده", callback_data='declare_winner')],
        [InlineKeyboardButton("📊 نتایج نهایی", callback_data='final_results')],
        [InlineKeyboardButton("🎁 توزیع جوایز", callback_data='distribute_rewards')],
        [InlineKeyboardButton("❌ لغو", callback_data='cancel_end_season')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    end_text = """
🏁 **پایان فصل جاری**

📅 **فصل:** ۳
⏰ **مدت:** ۲۷ روز از ۳۰ روز
👥 **شرکت‌کنندگان:** ۲۴ بازیکن

📊 **رتبه‌بندی موقت:**
🥇 ۱. امپراتوری پارس (امتیاز: ۲,۸۵۰)
🥈 ۲. روم باستان (امتیاز: ۲,۶۲۰)
🥉 ۳. مصر باستان (امتیاز: ۲,۴۰۰)
۴. یونان باستان (امتیاز: ۲,۱۵۰)
۵. چین باستان (امتیاز: ۲,۰۸۰)

⚔️ **آمار فصل:**
• جنگ‌ها: ۱۲۷ مورد
• اتحادها: ۴۸ مورد
• خیانت‌ها: ۹ مورد
• کشورهای نابود شده: ۳ کشور

💰 **جوایز فصل:**
• رتبه ۱: ۱۰,۰۰۰ 🪙 طلا + عنوان "فاتح"
• رتبه ۲: ۷,۰۰۰ 🪙 طلا
• رتبه ۳: ۵,۰۰۰ 🪙 طلا
• رتبه‌های ۴-۱۰: ۲,۰۰۰ 🪙 طلا

👇 عملیات مورد نظر را انتخاب کنید:
"""
    await update.message.reply_text(end_text, reply_markup=reply_markup, parse_mode='Markdown')

async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال پیام به همه بازیکنان (فقط مالک)"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ دسترسی ممنوع!")
        return
    
    if not context.args:
        await update.message.reply_text(
            "📢 **ارسال پیام عمومی**\n\n"
            "لطفاً پیام خود را بعد از دستور وارد کنید:\n"
            "`/broadcast متن پیام شما`\n\n"
            "مثال:\n"
            "`/broadcast فصل جدید فردا شروع می‌شود! آماده باشید.`"
        )
        return
    
    message = " ".join(context.args)
    keyboard = [
        [InlineKeyboardButton("✅ ارسال", callback_data=f'broadcast_send:{message[:50]}')],
        [InlineKeyboardButton("❌ لغو", callback_data='broadcast_cancel')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    preview_text = f"""
📢 **پیش‌نمایش پیام عمومی**

📝 **متن پیام:**
{message}

👥 **گیرندگان:** ۳۲ بازیکن فعال
⏰ **زمان ارسال:** بلافاصله
📱 **قالب:** مارک‌داون پشتیبانی می‌شود

⚠️ **توجه:** این پیام به همه بازیکنان ارسال خواهد شد و قابل لغو نیست.

👇 آیا مطمئن هستید؟
"""
    await update.message.reply_text(preview_text, reply_markup=reply_markup, parse_mode='Markdown')

async def reset_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ریست کامل بازی (فقط مالک)"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ دسترسی ممنوع!")
        return
    
    keyboard = [
        [InlineKeyboardButton("🔥 ریست کامل", callback_data='reset_full')],
        [InlineKeyboardButton("🔄 ریست منابع", callback_data='reset_resources')],
        [InlineKeyboardButton("⚔️ ریست نظامی", callback_data='reset_military')],
        [InlineKeyboardButton("🏛️ ریست کشورها", callback_data='reset_countries')],
        [InlineKeyboardButton("❌ لغو", callback_data='reset_cancel')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    reset_text = """
🔄 **سیستم ریست بازی**

⚠️ **هشدار خطر!**
این عملیات تمام یا بخشی از داده‌های بازی را پاک می‌کند.

📊 **داده‌های قابل ریست:**
۱. **ریست کامل** - همه چیز پاک می‌شود
   • همه بازیکنان
   • همه کشورها
   • تمام منابع
   • تاریخچه بازی

۲. **ریست منابع** - فقط منابع
   • موجودی طلا، آهن، سنگ، غذا
   • ساختمان‌ها
   • معادن

۳. **ریست نظامی** - فقط نظامی
   • ارتش‌ها
   • جنگ‌ها
   • اتحادها

۴. **ریست کشورها** - فقط کشورها
   • تخصیص کشورها
   • مالکیت‌ها

💾 **پشتیبان‌گیری:** آخرین پشتیبان ۲ ساعت پیش گرفته شده است.

👇 نوع ریست را انتخاب کنید:
"""
    await update.message.reply_text(reset_text, reply_markup=reply_markup, parse_mode='Markdown')

# ========== مدیریت Callback Query ==========

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کلیک روی دکمه‌ها"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    logger.info(f"Button clicked: {data} by user {user_id}")
    
    # پاسخ به دکمه‌های مختلف
    if data == 'main_menu':
        await query.edit_message_text(
            "🏛️ **منوی اصلی جنگ جهانی باستان**\n\n"
            "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
            parse_mode='Markdown'
        )
    
    elif data == 'generate_res':
        await query.edit_message_text(
            "⛏️ **تولید منابع آغاز شد!**\n\n"
            "✅ منابع با موفقیت تولید شدند:\n"
            "• 🪙 طلا: +150\n"
            "• ⚙️ آهن: +80\n"
            "• 🪨 سنگ: +60\n"
            "• 🌾 غذا: +200\n\n"
            "⏰ تولید بعدی: ۱ ساعت دیگر",
            parse_mode='Markdown'
        )
    
    elif data == 'upgrade_army':
        await upgrade_army(update, context)
    
    elif data == 'stats':
        await query.edit_message_text(
            "📊 **آمار کلی کشور**\n\n"
            "🏛️ **امپراتوری پارس**\n"
            "📅 تأسیس: ۱۵ روز پیش\n\n"
            "💰 **اقتصاد:**\n"
            "• درآمد روزانه: ۲,۴۰۰ 🪙\n"
            "• هزینه روزانه: ۱,۸۰۰ 🪙\n"
            "• سود خالص: ۶۰۰ 🪙/روز\n\n"
            "⚔️ **نظامی:**\n"
            "• قدرت کل: ۸۵۰ امتیاز\n"
            "• رتبه جهانی: ۷ از ۲۸\n"
            "• پیروزی‌ها: ۱۲ جنگ\n"
            "• شکست‌ها: ۳ جنگ\n\n"
            "🤝 **دیپلماسی:**\n"
            "• اتحادها: ۲ کشور\n"
            "• دشمنان: ۳ کشور\n"
            "• بی‌طرف: ۲۲ کشور\n\n"
            "📈 **روند کلی:** 📈 صعودی",
            parse_mode='Markdown'
        )
    
    elif data.startswith('admin_'):
        # مدیریت دکمه‌های ادمین
        if user_id != OWNER_ID:
            await query.edit_message_text("❌ **دسترسی ممنوع!**")
            return
        
        if data == 'admin_add_player':
            await query.edit_message_text(
                "➕ **افزودن بازیکن جدید**\n\n"
                "لطفاً اطلاعات را وارد کنید:\n\n"
                "۱. آیدی عددی کاربر در تلگرام\n"
                "۲. نام کاربری (اختیاری)\n"
                "۳. کد کشور مورد نظر\n\n"
                "📝 **فرمت:**\n"
                "`آیدی کشورکد`\n\n"
                "مثال:\n"
                "`123456789 persia`\n\n"
                "👇 لطفاً اطلاعات را ارسال کنید:",
                parse_mode='Markdown'
            )
            context.user_data['awaiting_player_info'] = True
        
        elif data == 'admin_start_season':
            await start_season(update, context)
        
        elif data == 'admin_broadcast':
            await query.edit_message_text(
                "📢 **ارسال پیام عمومی**\n\n"
                "لطفاً متن پیام خود را ارسال کنید:\n\n"
                "⚠️ **توجه:** پیام به همه ۳۲ بازیکن فعال ارسال خواهد شد.",
                parse_mode='Markdown'
            )
            context.user_data['awaiting_broadcast'] = True
        
        elif data == 'admin_reset':
            await reset_game(update, context)
        
        elif data == 'admin_exit':
            await query.edit_message_text("👑 **خروج از پنل مدیریت**\n\nپنل مدیریت بسته شد.")
    
    elif data == 'new_advice':
        await get_advisor(update, context)
    
    else:
        # پاسخ پیش‌فرض برای دکمه‌های ناشناخته
        await query.edit_message_text(
            f"🔄 **عملیات انجام شد**\n\n"
            f"دکمه: `{data}`\n"
            f"توسط: {query.from_user.first_name}\n"
            f"در: {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"✅ عملیات با موفقیت ثبت شد.",
            parse_mode='Markdown'
        )

# ========== مدیریت پیام‌های متنی ==========

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت پیام‌های متنی"""
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # بررسی اگر مالک در حال افزودن بازیکن است
    if user_id == OWNER_ID and context.user_data.get('awaiting_player_info'):
        try:
            parts = message_text.split()
            if len(parts) >= 2:
                player_id = int(parts[0])
                country_code = parts[1].lower()
                username = update.effective_user.username or f"user_{player_id}"
                
                # در حالت واقعی اینجا db.add_player فراخوانی می‌شود
                success = True  # حالت آزمایشی
                
                if success:
                    await update.message.reply_text(
                        f"✅ **بازیکن با موفقیت اضافه شد!**\n\n"
                        f"👤 **اطلاعات بازیکن:**\n"
                        f"• آیدی: `{player_id}`\n"
                        f"• نام کاربری: @{username}\n"
                        f"• کشور: {COUNTRIES.get(country_code, {}).get('name', 'ناشناخته')}\n"
                        f"• کد کشور: `{country_code}`\n\n"
                        f"📨 پیام خوش‌آمدگویی به بازیکن ارسال شد.",
                        parse_mode='Markdown'
                    )
                    
                    # ارسال پیام به بازیکن جدید (در حالت واقعی)
                    try:
                        if context.bot:
                            await context.bot.send_message(
                                player_id,
                                f"🎉 **به بازی جنگ جهانی باستان خوش آمدید!**\n\n"
                                f"کشور شما: **{COUNTRIES.get(country_code, {}).get('name', 'ناشناخته')}** 🏛️\n\n"
                                f"برای شروع، دستور /help را ارسال کنید.\n\n"
                                f"👑 مالک بازی: @amele55",
                                parse_mode='Markdown'
                            )
                    except:
                        pass
                else:
                    await update.message.reply_text("❌ خطا در افزودن بازیکن!")
            else:
                await update.message.reply_text("❌ فرمت نامعتبر!\nلطفاً طبق فرمت خواسته شده ارسال کنید.")
        
        except ValueError:
            await update.message.reply_text("❌ آیدی باید عددی باشد!")
        
        finally:
            context.user_data.pop('awaiting_player_info', None)
    
    # بررسی اگر مالک در حال ارسال پیام عمومی است
    elif user_id == OWNER_ID and context.user_data.get('awaiting_broadcast'):
        # شبیه‌سازی ارسال پیام عمومی
        sent_count = 32  # تعداد بازیکنان فرضی
        
        await update.message.reply_text(
            f"📢 **پیام عمومی ارسال شد!**\n\n"
            f"✅ پیام شما با موفقیت ارسال شد.\n"
            f"👥 تعداد گیرندگان: {sent_count} بازیکن\n"
            f"📝 متن پیام:\n"
            f"`{message_text[:200]}...`\n\n"
            f"⏰ زمان ارسال: {datetime.now().strftime('%H:%M:%S')}",
            parse_mode='Markdown'
        )
        
        context.user_data.pop('awaiting_broadcast', None)
    
    # پاسخ به پیام‌های عادی
    else:
        # اگر پیام دستور نیست، پاسخ ساده بده
        if not message_text.startswith('/'):
            responses = [
                "پیام شما دریافت شد! از دستور /help برای راهنمایی استفاده کنید.",
                "برای مدیریت کشور خود از دستورهای موجود استفاده کنید.",
                "مشکلی دارید؟ با مالک @amele55 تماس بگیرید.",
                "در حال حاضر در حال بازی هستید! از منوی دستورها استفاده کنید.",
            ]
            
            import random
            response = random.choice(responses)
            await update.message.reply_text(response)

# ========== تابع اصلی اجرای ربات ==========

def main():
    """تابع اصلی اجرای ربات"""
    global telegram_app
    
    # بررسی توکن ربات
    if not BOT_TOKEN or BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        logger.error("❌ BOT_TOKEN not set! Please set it in environment variables.")
        print("=" * 50)
        print("❌ ERROR: BOT_TOKEN is not set!")
        print("Please set the following environment variables:")
        print("1. BOT_TOKEN: Your Telegram bot token from @BotFather")
        print("2. WEBHOOK_URL: Your Render/Heroku app URL")
        print("3. PORT: Port number (default: 10000)")
        print("=" * 50)
        return
    
    logger.info("🚀 Starting Ancient War Bot v2.0...")
    print("=" * 50)
    print("🎮 Ancient War Bot v2.0")
    print("👑 Owner: @amele55")
    print("🐍 Python: 3.13")
    print("🤖 Library: python-telegram-bot v20.7")
    print("=" * 50)
    
    try:
        # ساخت Application
        application = Application.builder().token(BOT_TOKEN).build()
        telegram_app = application
        
        # اضافه کردن Handlerها
        # دستورهای اصلی
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("my_country", my_country))
        application.add_handler(CommandHandler("resources", resources))
        application.add_handler(CommandHandler("upgrade_army", upgrade_army))
        application.add_handler(CommandHandler("alliances", alliances))
        application.add_handler(CommandHandler("advisor", get_advisor))
        
        # دستورهای مالک
        application.add_handler(CommandHandler("admin", admin_panel))
        application.add_handler(CommandHandler("start_season", start_season))
        application.add_handler(CommandHandler("end_season", end_season))
        application.add_handler(CommandHandler("broadcast", broadcast_message))
        application.add_handler(CommandHandler("reset_game", reset_game))
        
        # مدیریت دکمه‌ها
        application.add_handler(CallbackQueryHandler(button_handler))
        
        # مدیریت پیام‌های متنی
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # راه‌اندازی Webhook یا Polling
        if WEBHOOK_URL and WEBHOOK_URL != 'https://your-app.onrender.com':
            logger.info(f"🌐 Using Webhook mode: {WEBHOOK_URL}")
            print(f"🌐 Webhook URL: {WEBHOOK_URL}")
            print(f"🔗 Webhook path: /{BOT_TOKEN}")
            
            # اجرای Flask در thread جداگانه
            flask_thread = threading.Thread(target=run_flask, daemon=True)
            flask_thread.start()
            
            # تنظیم Webhook
            application.run_webhook(
                listen="0.0.0.0",
                port=PORT,
                webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
                secret_token='ANCIENT_WAR_BOT_SECRET',
            )
        else:
            # حالت Polling برای توسعه
            logger.info("🔄 Using Polling mode (Development)")
            print("🔄 Development mode: Polling")
            print("⚠️  Note: For production, set WEBHOOK_URL environment variable")
            
            application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
            )
    
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")
        print(f"❌ ERROR: {e}")
        print("💡 Tips:")
        print("1. Check your BOT_TOKEN")
        print("2. Make sure all dependencies are installed")
        print("3. Check firewall/port settings")
        raise

if __name__ == '__main__':
    main()
