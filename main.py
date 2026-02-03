import os
import sys
import logging
from datetime import datetime
import threading
import json

# راه‌حل جایگزین برای imghdr در پایتون 3.13
try:
    import imghdr
except ImportError:
    # شبیه‌سازی imghdr برای پایتون 3.13
    import struct
    
    class ImghdrCompat:
        @staticmethod
        def what(file, h=None):
            if h is None:
                with open(file, 'rb') as f:
                    h = f.read(32)
            
            if len(h) < 32:
                return None
            
            # بررسی فرمت‌های تصویر
            if h.startswith(b'\xff\xd8\xff'):
                return 'jpeg'
            elif h.startswith(b'\x89PNG\r\n\x1a\n'):
                return 'png'
            elif h[:6] in (b'GIF87a', b'GIF89a'):
                return 'gif'
            elif h.startswith(b'BM'):
                return 'bmp'
            elif h.startswith(b'RIFF') and h[8:12] == b'WEBP':
                return 'webp'
            return None
    
    imghdr = ImghdrCompat()

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

# تنظیم لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ایجاد دیتابیس ساده در حافظه
class SimpleDatabase:
    def __init__(self):
        self.players = {}
        self.countries = {}
        self.armies = {}
        self.alliances = []
        self.init_data()
    
    def init_data(self):
        # کشورهای اولیه
        countries_data = {
            'persia': {'name': 'امپراتوری پارس', 'controller': 'AI', 'gold': 1000, 'iron': 500, 'stone': 500, 'food': 1000},
            'rome': {'name': 'امپراتوری روم', 'controller': 'AI', 'gold': 1000, 'iron': 500, 'stone': 500, 'food': 1000},
            'egypt': {'name': 'فراعنه مصر', 'controller': 'AI', 'gold': 1000, 'iron': 500, 'stone': 500, 'food': 1000},
            'china': {'name': 'امپراتوری چین', 'controller': 'AI', 'gold': 1000, 'iron': 500, 'stone': 500, 'food': 1000},
            'greece': {'name': 'یونان باستان', 'controller': 'AI', 'gold': 1000, 'iron': 500, 'stone': 500, 'food': 1000},
            'babylon': {'name': 'بابل', 'controller': 'AI', 'gold': 1000, 'iron': 500, 'stone': 500, 'food': 1000},
        }
        
        for code, data in countries_data.items():
            self.countries[code] = data
            self.armies[code] = {
                'soldiers': 100,
                'cavalry': 20,
                'siege': 5,
                'level': 1,
                'power': 125
            }
    
    def add_player(self, user_id, username, country_code):
        if str(user_id) in self.players:
            return False
        
        if country_code not in self.countries:
            return False
        
        self.players[str(user_id)] = {
            'username': username,
            'country_code': country_code,
            'join_date': datetime.now().isoformat()
        }
        
        self.countries[country_code]['controller'] = 'HUMAN'
        self.countries[country_code]['player_id'] = user_id
        
        return True
    
    def get_ai_countries(self):
        return [(code, data['name']) for code, data in self.countries.items() 
                if data.get('controller') == 'AI']
    
    def get_country_info_by_player(self, user_id):
        player = self.players.get(str(user_id))
        if not player:
            return None
        
        country_code = player['country_code']
        country = self.countries.get(country_code)
        army = self.armies.get(country_code, {})
        
        if not country:
            return None
        
        return {
            'code': country_code,
            'name': country['name'],
            'controller': country.get('controller', 'AI'),
            'gold': country.get('gold', 0),
            'iron': country.get('iron', 0),
            'stone': country.get('stone', 0),
            'food': country.get('food', 0),
            'soldiers': army.get('soldiers', 0),
            'cavalry': army.get('cavalry', 0),
            'siege': army.get('siege', 0),
            'level': army.get('level', 1),
            'power': army.get('power', 0)
        }

# ایجاد نمونه دیتابیس
db = SimpleDatabase()

# برنامه Flask
app = Flask(__name__)

# تنظیمات
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
OWNER_ID = 8588773170
WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
PORT = int(os.getenv('PORT', 10000))

telegram_app = None

@app.route('/')
def home():
    return '🏛️ Ancient War Bot v2.0 - Ready!'

@app.route('/webhook', methods=['POST'])
def webhook():
    if telegram_app:
        update = Update.de_json(request.get_json(force=True), telegram_app.bot)
        telegram_app.update_queue.put(update)
    return 'OK'

def run_flask():
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

# دستورهای ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"🤴 به جنگ جهانی باستان خوش آمدید {user.first_name}!\n\n"
        f"🏛️ یک بازی استراتژیک چندنفره\n"
        f"👑 مالک: @amele55\n"
        f"📱 ورژن: 2.0\n\n"
        f"برای شروع از /help استفاده کنید."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🎮 **دستورهای بازی:**

/start - شروع بازی
/help - راهنمایی
/my_country - وضعیت کشور
/resources - منابع کشور
/upgrade - ارتقای ارتش
/alliances - اتحادها
/advisor - مشاوره

👑 **دستورهای مالک:**
/admin - پنل مدیریت
/add_player - افزودن بازیکن
/broadcast - پیام عمومی
/reset - ریست بازی
"""
    await update.message.reply_text(help_text)

async def my_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    country = db.get_country_info_by_player(user_id)
    
    if country:
        text = f"""
🏛️ **{country['name']}**

💰 **منابع:**
طلا: {country['gold']}
آهن: {country['iron']}
سنگ: {country['stone']}
غذا: {country['food']}

⚔️ **ارتش:**
سربازان: {country['soldiers']}
سواره نظام: {country['cavalry']}
ماشین محاصره: {country['siege']}
سطح: {country['level']}
قدرت: {country['power']}
"""
        await update.message.reply_text(text)
    else:
        await update.message.reply_text(
            "شما هنوز کشوری ندارید.\n"
            "برای دریافت کشور با مالک (@amele55) تماس بگیرید."
        )

async def resources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⛏️ تولید منابع", callback_data='generate')],
        [InlineKeyboardButton("⚔️ ارتقا", callback_data='upgrade')],
        [InlineKeyboardButton("🏛️ بازگشت", callback_data='back')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "💰 **مدیریت منابع**\n\n"
        "منابع خود را مدیریت کنید:",
        reply_markup=reply_markup
    )

async def upgrade_army(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    country = db.get_country_info_by_player(user_id)
    
    if country and country['gold'] >= 500:
        # شبیه‌سازی ارتقا
        text = "✅ ارتش شما ارتقا یافت!\nسطح جدید: 2\nقدرت جدید: 250"
        await update.message.reply_text(text)
    else:
        await update.message.reply_text("❌ طلا کافی نیست یا کشور ندارید.")

async def alliances(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🤝 ایجاد اتحاد", callback_data='create_alliance')],
        [InlineKeyboardButton("📋 لیست کشورها", callback_data='list_countries')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤝 **سیستم اتحادها**\n\n"
        "با کشورهای دیگر متحد شوید:",
        reply_markup=reply_markup
    )

async def get_advisor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    advice = "👨‍💼 وزیر: منابع خود را مدیریت کنید و ارتش را تقویت نمایید."
    await update.message.reply_text(advice)

# دستورهای مالک
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ دسترسی ممنوع!")
        return
    
    keyboard = [
        [InlineKeyboardButton("➕ افزودن بازیکن", callback_data='add_player')],
        [InlineKeyboardButton("📢 پیام عمومی", callback_data='broadcast')],
        [InlineKeyboardButton("🔄 ریست", callback_data='reset')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👑 **پنل مدیریت**\n\n"
        "عملیات مورد نظر را انتخاب کنید:",
        reply_markup=reply_markup
    )

async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ دسترسی ممنوع!")
        return
    
    if not context.args:
        await update.message.reply_text("لطفا پیام را وارد کنید: /broadcast <پیام>")
        return
    
    message = " ".join(context.args)
    await update.message.reply_text(f"✅ پیام ارسال شد: {message}")

async def add_player_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ دسترسی ممنوع!")
        return
    
    if not context.args:
        # نمایش کشورهای AI
        ai_countries = db.get_ai_countries()
        keyboard = []
        for code, name in ai_countries:
            keyboard.append([InlineKeyboardButton(name, callback_data=f'add_{code}')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🔍 **کشورهای قابل تخصیص:**\n\n"
            "یکی را انتخاب کنید:",
            reply_markup=reply_markup
        )
        return

# مدیریت دکمه‌ها
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == 'generate':
        await query.edit_message_text("✅ منابع تولید شدند!")
    elif data == 'upgrade':
        await upgrade_army(update, context)
    elif data.startswith('add_'):
        country_code = data[4:]
        context.user_data['selected_country'] = country_code
        await query.edit_message_text(f"کشور انتخاب شد. لطفا آیدی بازیکن را ارسال کنید.")
    elif data == 'broadcast':
        context.user_data['awaiting_broadcast'] = True
        await query.edit_message_text("لطفا متن پیام را ارسال کنید:")
    else:
        await query.edit_message_text(f"✅ عملیات انجام شد: {data}")

# مدیریت پیام‌ها
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    # افزودن بازیکن
    if user_id == OWNER_ID and 'selected_country' in context.user_data:
        try:
            player_id = int(text)
            country_code = context.user_data['selected_country']
            
            success = db.add_player(player_id, f"user_{player_id}", country_code)
            
            if success:
                await update.message.reply_text(f"✅ بازیکن {player_id} اضافه شد.")
                # ارسال پیام به بازیکن
                try:
                    await context.bot.send_message(
                        player_id,
                        "🎉 به بازی خوش آمدید!\nکشور شما تخصیص یافت."
                    )
                except:
                    pass
            else:
                await update.message.reply_text("❌ خطا در افزودن بازیکن.")
            
            del context.user_data['selected_country']
        except ValueError:
            await update.message.reply_text("❌ آیدی باید عددی باشد.")
    
    # پیام عمومی
    elif user_id == OWNER_ID and context.user_data.get('awaiting_broadcast'):
        await update.message.reply_text(f"✅ پیام عمومی ارسال شد: {text}")
        del context.user_data['awaiting_broadcast']
    
    # پاسخ به پیام‌های عادی
    elif not text.startswith('/'):
        await update.message.reply_text(
            "پیام شما دریافت شد.\n"
            "از /help برای راهنمایی استفاده کنید."
        )

# تابع اصلی
def main():
    global telegram_app
    
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN not set!")
        print("لطفا متغیر محیطی BOT_TOKEN را تنظیم کنید.")
        return
    
    print("🚀 شروع ربات جنگ جهانی باستان...")
    
    try:
        # ساخت Application
        application = Application.builder().token(BOT_TOKEN).build()
        telegram_app = application
        
        # اضافه کردن Handlerها
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("my_country", my_country))
        application.add_handler(CommandHandler("resources", resources))
        application.add_handler(CommandHandler("upgrade", upgrade_army))
        application.add_handler(CommandHandler("alliances", alliances))
        application.add_handler(CommandHandler("advisor", get_advisor))
        application.add_handler(CommandHandler("admin", admin_panel))
        application.add_handler(CommandHandler("broadcast", broadcast_message))
        application.add_handler(CommandHandler("add_player", add_player_command))
        
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # راه‌اندازی
        if WEBHOOK_URL:
            print(f"🌐 استفاده از Webhook: {WEBHOOK_URL}")
            
            # اجرای Flask
            flask_thread = threading.Thread(target=run_flask, daemon=True)
            flask_thread.start()
            
            # تنظیم Webhook
            application.run_webhook(
                listen="0.0.0.0",
                port=PORT,
                webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
                secret_token='ANCIENT_WAR_SECRET',
            )
        else:
            print("🔄 استفاده از Polling (حالت توسعه)")
            application.run_polling()
    
    except Exception as e:
        print(f"❌ خطا: {e}")
        raise

if __name__ == '__main__':
    main()
