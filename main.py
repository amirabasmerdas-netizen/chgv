import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from flask import Flask, request
import threading
from datetime import datetime

from config import BOT_TOKEN, OWNER_ID, CHANNEL_ID, WEBHOOK_URL, PORT, COUNTRIES
from database import Database
from game_logic import GameLogic
from advisor import Advisor

# تنظیم لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ایجاد نمونه‌ها
db = Database()
game = GameLogic()
advisor = Advisor()

# برنامه Flask برای Webhook
app = Flask(__name__)

# ذخیره Application
telegram_app = None

@app.route('/')
def index():
    return 'Ancient War Bot is running!'

@app.route('/webhook', methods=['POST'])
def webhook():
    if telegram_app:
        update = Update.de_json(request.get_json(force=True), telegram_app.bot)
        telegram_app.update_queue.put(update)
    return 'OK'

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

# دستورهای ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"به جنگ جهانی باستان خوش آمدید {user.first_name}!\n\n"
        f"من ربات استراتژیک شما هستم. با مالک تماس بگیرید تا کشور خود را دریافت کنید.\n\n"
        f"مالک: @amele55\n"
        f"ورژن: 2.0"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🤖 **دستورهای ربات جنگ جهانی باستان:**

🔹 /start - شروع بازی
🔹 /help - راهنمایی
🔹 /my_country - مشاهده کشور خود
🔹 /resources - مشاهده منابع
🔹 /upgrade_army - ارتقای ارتش
🔹 /alliances - مشاهده اتحادها
🔹 /create_alliance <کد کشور> - ایجاد اتحاد
🔹 /advisor - مشاوره وزیر

👑 **دستورهای مالک:**
🔸 /admin - پنل مدیریت
🔸 /start_season - شروع فصل جدید
🔸 /end_season - پایان فصل
🔸 /broadcast <پیام> - ارسال پیام عمومی
🔸 /add_player - افزودن بازیکن جدید
🔸 /reset_game - ریست کل بازی
"""
    await update.message.reply_text(help_text)

async def my_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    country_info = db.get_country_info_by_player(user_id)
    
    if country_info:
        message = f"""
🏛️ **{country_info['name']}**

👤 کنترل: شما (بازیکن)
⚔️ سطح ارتش: {country_info.get('army_level', 1)}
💪 قدرت کل: {country_info.get('total_power', 0)}

💰 **منابع:**
• طلا: {country_info['gold']} 
• آهن: {country_info['iron']} 
• سنگ: {country_info['stone']} 
• غذا: {country_info['food']} 

👥 **نیروها:**
• سربازان: {country_info.get('soldiers', 0)} 
• سواره نظام: {country_info.get('cavalry', 0)} 
• ماشین‌های محاصره: {country_info.get('siege', 0)} 

📊 امتیاز قدرت: {country_info.get('power_score', 0)}
"""
        await update.message.reply_text(message)
    else:
        await update.message.reply_text("شما هنوز کشوری ندارید. با مالک تماس بگیرید.")

async def resources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    country_info = db.get_country_info_by_player(user_id)
    
    if country_info:
        keyboard = [
            [InlineKeyboardButton("⛏️ تولید منابع خودکار", callback_data='generate_resources')],
            [InlineKeyboardButton("⚔️ ارتقای ارتش", callback_data='upgrade_army')],
            [InlineKeyboardButton("🏛️ بازگشت به منوی اصلی", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = f"""
💰 **منابع {country_info['name']}:**

طلا: {country_info['gold']}
آهن: {country_info['iron']}
سنگ: {country_info['stone']}
غذا: {country_info['food']}

📊 **ارزش کل:** {country_info['gold'] + country_info['iron']*2 + country_info['stone'] + country_info['food']/10}
"""
        await update.message.reply_text(message, reply_markup=reply_markup)
    else:
        await update.message.reply_text("کشوری پیدا نشد.")

async def upgrade_army(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    country_info = db.get_country_info_by_player(user_id)
    
    if not country_info:
        await update.message.reply_text("کشوری پیدا نشد.")
        return
    
    success, message = db.upgrade_army(country_info['code'])
    
    if success:
        # ثبت رویداد
        db.add_event('ARMY_UPGRADE', 
                    f"{country_info['name']} ارتش خود را ارتقا داد",
                    [country_info['code']])
        
        await update.message.reply_text(f"✅ {message}")
    else:
        await update.message.reply_text(f"❌ {message}")

async def alliances(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    country_info = db.get_country_info_by_player(user_id)
    
    if not country_info:
        await update.message.reply_text("کشوری پیدا نشد.")
        return
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT c.name FROM alliances a
        JOIN countries c ON (
            (a.country1_code = c.code AND a.country2_code = ?) 
            OR (a.country2_code = c.code AND a.country1_code = ?)
        )
        WHERE a.is_active = 1
    ''', (country_info['code'], country_info['code']))
    
    allies = cursor.fetchall()
    conn.close()
    
    if allies:
        ally_list = "\n".join([f"• {ally[0]}" for ally in allies])
        message = f"🤝 **اتحادهای {country_info['name']}:**\n\n{ally_list}"
    else:
        message = "شما هیچ اتحادی ندارید."
    
    keyboard = [
        [InlineKeyboardButton("➕ ایجاد اتحاد جدید", callback_data='create_alliance')],
        [InlineKeyboardButton("📋 لیست کشورها", callback_data='list_countries')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=reply_markup)

async def create_alliance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("لطفا کد کشور را وارد کنید:\n/create_alliance <کد کشور>")
        return
    
    target_code = context.args[0]
    user_id = update.effective_user.id
    country_info = db.get_country_info_by_player(user_id)
    
    if not country_info:
        await update.message.reply_text("کشوری پیدا نشد.")
        return
    
    success, message = db.create_alliance(country_info['code'], target_code)
    
    if success:
        # ثبت رویداد
        target_info = db.get_country_info(target_code)
        if target_info:
            db.add_event('ALLIANCE_FORMED',
                        f"{country_info['name']} با {target_info['name']} اتحاد تشکیل داد",
                        [country_info['code'], target_code])
        
        await update.message.reply_text(f"✅ {message}")
    else:
        await update.message.reply_text(f"❌ {message}")

async def get_advisor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    country_info = db.get_country_info_by_player(user_id)
    
    if not country_info:
        await update.message.reply_text("کشوری پیدا نشد.")
        return
    
    advice = advisor.generate_advice(country_info['code'])
    
    if advice:
        await update.message.reply_text(advice['message'])
        
        # ذخیره پیام
        advisor.save_advice_message(country_info['code'], advice['message'])
    else:
        await update.message.reply_text("وزیر: وضعیت شما خوب است. ادامه دهید!")

# دستورهای مالک
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ دسترسی ممنوع!")
        return
    
    keyboard = [
        [InlineKeyboardButton("➕ افزودن بازیکن", callback_data='add_player')],
        [InlineKeyboardButton("🏁 شروع فصل", callback_data='start_season')],
        [InlineKeyboardButton("🏁 پایان فصل", callback_data='end_season')],
        [InlineKeyboardButton("📢 ارسال پیام عمومی", callback_data='broadcast')],
        [InlineKeyboardButton("🔄 ریست بازی", callback_data='reset_game')],
        [InlineKeyboardButton("📊 آمار بازی", callback_data='stats')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👑 **پنل مدیریت مالک**\n\n"
        "یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=reply_markup
    )

async def start_season(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ دسترسی ممنوع!")
        return
    
    season_id = db.start_season()
    
    # ارسال به کانال خبری
    if CHANNEL_ID:
        try:
            await context.bot.send_message(
                CHANNEL_ID,
                "🏁 **فصل جدید جنگ‌های باستان آغاز شد!**\n\n"
                "پادشاهان! جهان در انتظار فتح شماست!\n\n"
                "ساخته شده توسط @amele55\n"
                "ورژن 2 ربات"
            )
        except:
            pass
    
    await update.message.reply_text(f"✅ فصل جدید با شماره {season_id} آغاز شد!")

async def end_season(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ دسترسی ممنوع!")
        return
    
    winner = game.calculate_winner()
    
    if winner:
        db.end_season(winner['country_code'], winner['player_id'])
        
        # ارسال به کانال خبری
        if CHANNEL_ID:
            country_info = db.get_country_info(winner['country_code'])
            
            try:
                await context.bot.send_message(
                    CHANNEL_ID,
                    f"🏆 **پایان فصل جنگ‌های باستان**\n\n"
                    f"👑 فاتح نهایی جهان: {country_info['name']}\n"
                    f"👤 بازیکن: {winner['username']}\n\n"
                    f"ساخته شده توسط @amele55\n"
                    f"منتظر فصل بعد باشید!\n"
                    f"ورژن 2 ربات"
                )
            except:
                pass
        
        await update.message.reply_text(
            f"✅ فصل با موفقیت پایان یافت!\n"
            f"🏆 برنده: {winner['username']} ({country_info['name']})"
        )
    else:
        await update.message.reply_text("❌ برنده‌ای یافت نشد!")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ دسترسی ممنوع!")
        return
    
    if not context.args:
        await update.message.reply_text("لطفا پیام را وارد کنید:\n/broadcast <پیام>")
        return
    
    message = " ".join(context.args)
    
    # ارسال به همه بازیکنان
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT user_id FROM players WHERE is_active = 1')
    players = cursor.fetchall()
    conn.close()
    
    sent_count = 0
    for player in players:
        try:
            await context.bot.send_message(
                player[0],
                f"📢 **پیام عمومی از مالک:**\n\n{message}"
            )
            sent_count += 1
        except:
            continue
    
    await update.message.reply_text(f"✅ پیام به {sent_count} بازیکن ارسال شد.")

async def reset_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ دسترسی ممنوع!")
        return
    
    keyboard = [
        [InlineKeyboardButton("✅ بله، ریست کن", callback_data='confirm_reset')],
        [InlineKeyboardButton("❌ خیر، لغو", callback_data='cancel_reset')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚠️ **هشدار!**\n\n"
        "آیا مطمئن هستید که می‌خواهید کل بازی را ریست کنید؟\n"
        "این عمل تمام داده‌ها را پاک می‌کند.",
        reply_markup=reply_markup
    )

# مدیریت Callback Query
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if data == 'main_menu':
        await query.edit_message_text(
            "🏛️ **منوی اصلی**\n\n"
            "یکی از گزینه‌ها را انتخاب کنید:"
        )
    
    elif data == 'add_player':
        if user_id != OWNER_ID:
            await query.edit_message_text("❌ دسترسی ممنوع!")
            return
        
        # نمایش کشورهای AI
        ai_countries = db.get_ai_countries()
        
        keyboard = []
        for country in ai_countries:
            keyboard.append([InlineKeyboardButton(
                country[1],
                callback_data=f'select_country_{country[0]}'
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='admin_menu')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🔍 **کشورهای تحت کنترل AI:**\n\n"
            "یکی را برای تخصیص به بازیکن انتخاب کنید:",
            reply_markup=reply_markup
        )
    
    elif data.startswith('select_country_'):
        if user_id != OWNER_ID:
            await query.edit_message_text("❌ دسترسی ممنوع!")
            return
        
        country_code = data.replace('select_country_', '')
        context.user_data['selected_country'] = country_code
        
        await query.edit_message_text(
            f"کشور انتخاب شد. لطفا آیدی عددی بازیکن را ارسال کنید."
        )
    
    elif data == 'start_season':
        await start_season(update, context)
    
    elif data == 'end_season':
        await end_season(update, context)
    
    elif data == 'broadcast':
        await query.edit_message_text(
            "لطفا پیام عمومی را ارسال کنید:"
        )
        context.user_data['awaiting_broadcast'] = True
    
    elif data == 'confirm_reset':
        # پاک کردن و ایجاد مجدد دیتابیس
        db.__init__()
        await query.edit_message_text("✅ بازی با موفقیت ریست شد!")
    
    elif data == 'cancel_reset':
        await query.edit_message_text("❌ ریست بازی لغو شد.")
    
    elif data == 'admin_menu':
        await admin_panel(update, context)
    
    elif data == 'upgrade_army':
        await upgrade_army(update, context)
    
    elif data == 'generate_resources':
        # تولید منابع خودکار
        decisions = game.generate_resources()
        
        message = "✅ منابع خودکار تولید شدند!"
        if decisions:
            message += "\n\n🤖 **تصمیم‌های AI:**\n" + "\n".join(decisions)
        
        await query.edit_message_text(message)
    
    elif data == 'create_alliance':
        # نمایش کشورهای قابل اتحاد
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT code, name FROM countries WHERE controller_type = "AI"')
        countries = cursor.fetchall()
        conn.close()
        
        keyboard = []
        for country in countries:
            keyboard.append([InlineKeyboardButton(
                country[1],
                callback_data=f'ally_with_{country[0]}'
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='alliances')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🤝 **کشورهای قابل اتحاد:**\n\n"
            "یکی را برای پیشنهاد اتحاد انتخاب کنید:",
            reply_markup=reply_markup
        )
    
    elif data.startswith('ally_with_'):
        target_code = data.replace('ally_with_', '')
        
        # یافتن کشور بازیکن
        country_info = db.get_country_info_by_player(user_id)
        if country_info:
            success, message = db.create_alliance(country_info['code'], target_code)
            await query.edit_message_text(f"{'✅' if success else '❌'} {message}")
        else:
            await query.edit_message_text("❌ کشور شما یافت نشد!")
    
    elif data == 'stats':
        if user_id != OWNER_ID:
            await query.edit_message_text("❌ دسترسی ممنوع!")
            return
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # آمار بازی
        cursor.execute('SELECT COUNT(*) FROM players WHERE is_active = 1')
        player_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM countries WHERE controller_type = "AI"')
        ai_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM alliances WHERE is_active = 1')
        alliance_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT * FROM seasons WHERE is_active = 1')
        active_season = cursor.fetchone()
        
        conn.close()
        
        stats_message = f"""
📊 **آمار بازی:**

👥 بازیکنان انسانی: {player_count}
🤖 کشورهای AI: {ai_count}
🤝 اتحادهای فعال: {alliance_count}

{'🏁 **فصل فعال:** بله' if active_season else '🚫 **فصل فعال:** خیر'}
"""
        
        await query.edit_message_text(stats_message)

# مدیریت پیام‌های متنی
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # بررسی اگر مالک در حال افزودن بازیکن است
    if user_id == OWNER_ID and 'selected_country' in context.user_data:
        try:
            new_player_id = int(message_text)
            country_code = context.user_data['selected_country']
            
            # اضافه کردن بازیکن
            username = update.effective_user.username or f"user_{new_player_id}"
            success = db.add_player(new_player_id, username, country_code)
            
            if success:
                # اطلاع به بازیکن جدید
                try:
                    country_info = db.get_country_info(country_code)
                    await context.bot.send_message(
                        new_player_id,
                        f"🎉 **به بازی جنگ جهانی باستان خوش آمدید!**\n\n"
                        f"کشور شما: **{country_info['name']}** 🏛️\n\n"
                        f"برای شروع از دستور /help استفاده کنید."
                    )
                except Exception as e:
                    logger.error(f"Failed to send welcome message: {e}")
                
                await update.message.reply_text(
                    f"✅ بازیکن {new_player_id} به کشور {country_info['name']} تخصیص یافت."
                )
            else:
                await update.message.reply_text("❌ بازیکن از قبل وجود دارد.")
            
            del context.user_data['selected_country']
            
        except ValueError:
            await update.message.reply_text("❌ آیدی باید عددی باشد!")
    
    # بررسی اگر مالک در حال ارسال پیام عمومی است
    elif user_id == OWNER_ID and context.user_data.get('awaiting_broadcast'):
        # ارسال پیام عمومی
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT user_id FROM players WHERE is_active = 1')
        players = cursor.fetchall()
        conn.close()
        
        sent_count = 0
        for player in players:
            try:
                await context.bot.send_message(
                    player[0],
                    f"📢 **پیام عمومی از مالک:**\n\n{message_text}"
                )
                sent_count += 1
            except:
                continue
        
        await update.message.reply_text(f"✅ پیام به {sent_count} بازیکن ارسال شد.")
        context.user_data['awaiting_broadcast'] = False

# تابع اصلی اجرای ربات
def main():
    global telegram_app
    
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set in environment variables!")
        return
    
    # ساخت Application
    application = Application.builder().token(BOT_TOKEN).build()
    telegram_app = application
    
    # اضافه کردن handlerها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("my_country", my_country))
    application.add_handler(CommandHandler("resources", resources))
    application.add_handler(CommandHandler("upgrade_army", upgrade_army))
    application.add_handler(CommandHandler("alliances", alliances))
    application.add_handler(CommandHandler("create_alliance", create_alliance))
    application.add_handler(CommandHandler("advisor", get_advisor))
    
    # دستورهای مالک
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("start_season", start_season))
    application.add_handler(CommandHandler("end_season", end_season))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("reset_game", reset_game))
    
    # Callback Query
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # پیام‌های متنی
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # تنظیم Webhook
    if WEBHOOK_URL:
        # اجرای Flask در thread جداگانه
        flask_thread = threading.Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()
        
        # تنظیم Webhook
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
        )
    else:
        # استفاده از polling برای تست
        logger.info("Using polling mode (WEBHOOK_URL not set)")
        application.run_polling()

if __name__ == '__main__':
    main()
