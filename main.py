import os
import logging
import sys
from datetime import datetime
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, CallbackQueryHandler,
    MessageHandler, Filters, CallbackContext
)
from apscheduler.schedulers.background import BackgroundScheduler

# شبیه‌سازی imghdr برای پایتون 3.13
if sys.version_info >= (3, 13):
    import types
    imghdr_module = types.ModuleType('imghdr')
    
    def what(file, h=None):
        """پیاده‌سازی ساده imghdr.what"""
        try:
            if hasattr(file, 'read'):
                file.seek(0)
                header = file.read(32)
            else:
                with open(file, 'rb') as f:
                    header = f.read(32)
        except:
            return None
        
        if header.startswith(b'\xff\xd8\xff'):
            return 'jpeg'
        elif header.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'png'
        elif header.startswith(b'GIF87a') or header.startswith(b'GIF89a'):
            return 'gif'
        elif header.startswith(b'BM'):
            return 'bmp'
        return None
    
    imghdr_module.what = what
    sys.modules['imghdr'] = imghdr_module

# ایمپورت config
try:
    from config import BOT_TOKEN, OWNER_ID, PORT, LISTEN, WEBHOOK_URL
    from database import Database
    from game_logic import GameLogic
    from advisor import Advisor
except ImportError as e:
    logging.error(f"خطا در ایمپورت ماژول‌ها: {e}")
    # مقادیر پیش‌فرض برای تست
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    OWNER_ID = 8588773170
    PORT = int(os.getenv("PORT", 8443))
    LISTEN = "0.0.0.0"
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# اشیاء اصلی
try:
    db = Database()
    game = GameLogic()
    advisor = Advisor()
except Exception as e:
    db = None
    game = None
    advisor = None
    logger.warning(f"ایجاد اشیاء بازی با مشکل مواجه شد: {e}")

# Flask app برای Webhook
app = Flask(__name__)

# ذخیره updater تلگرام
updater = None

def create_inline_keyboard(buttons_list, columns=2):
    """ایجاد کیبورد اینلاین از لیست دکمه‌ها"""
    keyboard = []
    row = []
    
    for i, button in enumerate(buttons_list):
        row.append(button)
        if (i + 1) % columns == 0:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    return InlineKeyboardMarkup(keyboard)

def start_command(update: Update, context: CallbackContext):
    """دستور /start"""
    try:
        user = update.effective_user
        user_id = user.id
        
        # بررسی آیا بازیکن کشور دارد؟
        if db:
            player_country = db.get_player_country(user_id)
        else:
            player_country = None
        
        if player_country:
            # نمایش داشبورد بازیکن
            show_player_dashboard(update, context, user_id)
        else:
            # خوش‌آمدگویی به کاربر جدید
            update.message.reply_text(
                text=f"👑 خوش آمدی {user.full_name}!\n\n"
                "به بازی استراتژیک **جنگ جهانی باستان** خوش آمدی!\n"
                "در حال حاضر شما کشوری ندارید.\n\n"
                "برای افزودن بازیکن، مالک ربات باید از طریق منو مدیریت اقدام کند."
            )
    except Exception as e:
        logger.error(f"خطا در start_command: {e}")
        update.message.reply_text("خطا در پردازش درخواست!")

def show_player_dashboard(update: Update, context: CallbackContext, user_id):
    """نمایش داشبورد بازیکن"""
    try:
        if not db:
            update.message.reply_text("خطا در اتصال به پایگاه داده!")
            return
            
        player_country = db.get_player_country(user_id)
        
        if not player_country:
            update.message.reply_text("شما کشوری ندارید!")
            return
        
        # دریافت اطلاعات
        resources = db.get_country_resources(player_country['id'])
        army = db.get_country_army(player_country['id'])
        
        # ایجاد متن داشبورد
        dashboard_text = (
            f"{player_country['color']} **{player_country['name']}**\n"
            f"👤 فرمانروا: {update.effective_user.full_name}\n"
            f"🎖️ تخصص: {player_country['specialty']}\n\n"
            
            f"💰 **منابع:**\n"
            f"• طلا: {resources['gold'] if resources else 0} 🪙\n"
            f"• آهن: {resources['iron'] if resources else 0} ⚒️\n"
            f"• سنگ: {resources['stone'] if resources else 0} 🪨\n"
            f"• غذا: {resources['food'] if resources else 0} 🌾\n\n"
            
            f"⚔️ **ارتش:**\n"
            f"• سطح: {army['level'] if army else 1} 🏆\n"
            f"• پیاده‌نظام: {army['infantry'] if army else 100} 🛡️\n"
            f"• سواره‌نظام: {army['cavalry'] if army else 20} 🐎\n"
            f"• تیرانداز: {army['archers'] if army else 30} 🏹\n"
            f"• قدرت کل: {army['power'] if army else 150} ⚡\n"
            f"• دفاع: {army['defense'] if army else 50} 🛡️\n"
        )
        
        # ایجاد دکمه‌های داشبورد
        buttons = [
            InlineKeyboardButton("🔄 به‌روزرسانی", callback_data="refresh_dashboard"),
            InlineKeyboardButton("⚔️ ارتقا ارتش", callback_data="upgrade_army"),
            InlineKeyboardButton("💰 جمع‌آوری منابع", callback_data="collect_resources"),
            InlineKeyboardButton("🤝 اتحادها", callback_data="show_alliances"),
            InlineKeyboardButton("👑 مشاوره وزیر", callback_data="get_advice"),
            InlineKeyboardButton("🏆 رده‌بندی", callback_data="show_ranking"),
        ]
        
        keyboard = create_inline_keyboard(buttons, columns=2)
        
        if update.callback_query:
            update.callback_query.edit_message_text(
                text=dashboard_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        else:
            update.message.reply_text(
                text=dashboard_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"خطا در show_player_dashboard: {e}")
        update.message.reply_text("خطا در نمایش داشبورد!")

def button_callback_handler(update: Update, context: CallbackContext):
    """مدیریت کلیک روی دکمه‌های اینلاین"""
    try:
        query = update.callback_query
        query.answer()
        
        user_id = query.from_user.id
        data = query.data
        
        if data == "refresh_dashboard":
            show_player_dashboard(update, context, user_id)
        
        elif data == "upgrade_army":
            upgrade_army(update, context, user_id)
        
        elif data == "collect_resources":
            collect_resources(update, context, user_id)
        
        elif data == "get_advice":
            send_advisor_advice(update, context, user_id)
        
        elif data == "show_ranking":
            show_ranking(update, context)
        
        elif data == "show_alliances":
            show_alliances(update, context, user_id)
        
        elif data.startswith("assign_country_"):
            if user_id == OWNER_ID:
                country_id = int(data.split("_")[2])
                context.user_data['selected_country'] = country_id
                query.edit_message_text(
                    text="کشور انتخاب شد. لطفاً آیدی عددی بازیکن را ارسال کنید:",
                    parse_mode='Markdown'
                )
        
        elif data.startswith("admin_"):
            if user_id == OWNER_ID:
                handle_admin_commands(update, context, data)
    
    except Exception as e:
        logger.error(f"خطا در button_callback_handler: {e}")

def upgrade_army(update: Update, context: CallbackContext, user_id):
    """ارتقای ارتش"""
    try:
        if not db:
            update.callback_query.message.reply_text("خطا در اتصال به پایگاه داده!")
            return
            
        player_country = db.get_player_country(user_id)
        
        if not player_country:
            update.callback_query.message.reply_text("شما کشوری ندارید!")
            return
        
        army = db.get_country_army(player_country['id'])
        resources = db.get_country_resources(player_country['id'])
        
        if not army or not resources:
            update.callback_query.message.reply_text("اطلاعات ارتش یا منابع یافت نشد!")
            return
        
        # هزینه ارتقا
        upgrade_cost = {
            'gold': army['level'] * 200,
            'iron': army['level'] * 100,
            'food': army['level'] * 150
        }
        
        # بررسی منابع کافی
        if (resources['gold'] >= upgrade_cost['gold'] and
            resources['iron'] >= upgrade_cost['iron'] and
            resources['food'] >= upgrade_cost['food']):
            
            # ارتقا ارتش
            db.upgrade_army_level(player_country['id'], upgrade_cost)
            
            update.callback_query.message.reply_text(
                text=f"✅ ارتش {player_country['name']} به سطح {army['level'] + 1} ارتقا یافت!\n"
                f"💰 هزینه: طلا:{upgrade_cost['gold']} آهن:{upgrade_cost['iron']} غذا:{upgrade_cost['food']}"
            )
        else:
            update.callback_query.message.reply_text(
                text=f"❌ منابع کافی برای ارتقا ندارید!\n"
                f"💰 نیاز: طلا:{upgrade_cost['gold']} آهن:{upgrade_cost['iron']} غذا:{upgrade_cost['food']}\n"
                f"💰 دارایی: طلا:{resources['gold']} آهن:{resources['iron']} غذا:{resources['food']}"
            )
    except Exception as e:
        logger.error(f"خطا در upgrade_army: {e}")
        update.callback_query.message.reply_text("خطا در ارتقای ارتش!")

def collect_resources(update: Update, context: CallbackContext, user_id):
    """جمع‌آوری منابع"""
    try:
        if not db:
            update.callback_query.message.reply_text("خطا در اتصال به پایگاه داده!")
            return
            
        player_country = db.get_player_country(user_id)
        
        if not player_country:
            update.callback_query.message.reply_text("شما کشوری ندارید!")
            return
        
        # افزایش منابع تصادفی
        resource_gains = {
            'gold': 50,
            'iron': 30,
            'stone': 40,
            'food': 80
        }
        
        db.update_resources(player_country['id'], resource_gains)
        
        update.callback_query.message.reply_text(
            text=f"✅ منابع جمع‌آوری شد!\n"
            f"🪙 طلا: +{resource_gains['gold']}\n"
            f"⚒️ آهن: +{resource_gains['iron']}\n"
            f"🪨 سنگ: +{resource_gains['stone']}\n"
            f"🌾 غذا: +{resource_gains['food']}"
        )
    except Exception as e:
        logger.error(f"خطا در collect_resources: {e}")
        update.callback_query.message.reply_text("خطا در جمع‌آوری منابع!")

def send_advisor_advice(update: Update, context: CallbackContext, user_id):
    """ارسال مشاوره وزیر"""
    try:
        if not advisor:
            update.callback_query.message.reply_text("سیستم مشاوره در دسترس نیست!")
            return
            
        advice = advisor.send_advice_to_player(user_id)
        
        if advice:
            update.callback_query.message.reply_text(text=advice, parse_mode='Markdown')
        else:
            update.callback_query.message.reply_text("در حال حاضر مشاوره‌ای موجود نیست.")
    except Exception as e:
        logger.error(f"خطا در send_advisor_advice: {e}")
        update.callback_query.message.reply_text("خطا در دریافت مشاوره!")

def show_ranking(update: Update, context: CallbackContext):
    """نمایش رده‌بندی"""
    try:
        if not db:
            update.callback_query.message.reply_text("خطا در اتصال به پایگاه داده!")
            return
            
        cursor = db.conn.cursor()
        cursor.execute('''
        SELECT c.name, c.color, a.power, a.level, 
               CASE WHEN c.controller = 'HUMAN' THEN '👤' ELSE '🤖' END as controller
        FROM army a
        JOIN countries c ON a.country_id = c.id
        WHERE c.is_active = 1
        ORDER BY a.power DESC
        LIMIT 10
        ''')
        
        rankings = cursor.fetchall()
        
        if not rankings:
            update.callback_query.message.reply_text("هنوز رده‌بندی‌ای موجود نیست.")
            return
        
        ranking_text = "🏆 **رده‌بندی قدرتمندترین کشورها:**\n\n"
        
        for i, country in enumerate(rankings, 1):
            medal = ""
            if i == 1: medal = "🥇"
            elif i == 2: medal = "🥈"
            elif i == 3: medal = "🥉"
            else: medal = f"{i}."
            
            ranking_text += (
                f"{medal} {country['color']} **{country['name']}** {country['controller']}\n"
                f"   ⚡ قدرت: {country['power']} | 🏆 سطح: {country['level']}\n"
            )
        
        update.callback_query.message.reply_text(text=ranking_text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"خطا در show_ranking: {e}")
        update.callback_query.message.reply_text("خطا در نمایش رده‌بندی!")

def show_alliances(update: Update, context: CallbackContext, user_id):
    """نمایش اتحادها"""
    try:
        if not db:
            update.callback_query.message.reply_text("خطا در اتصال به پایگاه داده!")
            return
            
        player_country = db.get_player_country(user_id)
        
        if not player_country:
            update.callback_query.message.reply_text("شما کشوری ندارید!")
            return
        
        cursor = db.conn.cursor()
        cursor.execute('''
        SELECT 
            c1.name as country1,
            c2.name as country2,
            a.relation_type,
            a.strength
        FROM alliances a
        JOIN countries c1 ON a.country1_id = c1.id
        JOIN countries c2 ON a.country2_id = c2.id
        WHERE c1.id = ? OR c2.id = ?
        ORDER BY a.relation_type
        ''', (player_country['id'], player_country['id']))
        
        alliances = cursor.fetchall()
        
        if not alliances:
            alliance_text = f"🌍 **{player_country['name']}** هیچ اتحادی ندارد.\n"
            alliance_text += "از منوی اصلی برای تشکیل اتحاد اقدام کن."
        else:
            alliance_text = f"🤝 **اتحادهای {player_country['name']}:**\n\n"
            
            for alliance in alliances:
                relation_emoji = "🛡️" if alliance['relation_type'] == 'ALLIANCE' else "⚔️"
                relation_text = "اتحاد" if alliance['relation_type'] == 'ALLIANCE' else "جنگ"
                
                alliance_text += (
                    f"{relation_emoji} **{alliance['country1']}** ↔ **{alliance['country2']}\n"
                    f"   📊 رابطه: {relation_text} | 💪 قدرت: {alliance['strength']}%\n"
                )
        
        update.callback_query.message.reply_text(text=alliance_text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"خطا در show_alliances: {e}")
        update.callback_query.message.reply_text("خطا در نمایش اتحادها!")

# ------------------ ADMIN COMMANDS ------------------

def admin_panel(update: Update, context: CallbackContext):
    """پنل مدیریت برای مالک"""
    try:
        if update.effective_user.id != OWNER_ID:
            update.message.reply_text("❌ فقط مالک ربات می‌تواند از این دستور استفاده کند!")
            return
        
        buttons = [
            InlineKeyboardButton("➕ افزودن بازیکن", callback_data="admin_add_player"),
            InlineKeyboardButton("🎮 شروع فصل جدید", callback_data="admin_start_season"),
            InlineKeyboardButton("🏁 پایان فصل", callback_data="admin_end_season"),
            InlineKeyboardButton("📢 ارسال پیام عمومی", callback_data="admin_broadcast"),
            InlineKeyboardButton("🔄 ریست بازی", callback_data="admin_reset_game"),
            InlineKeyboardButton("📊 آمار بازی", callback_data="admin_stats"),
        ]
        
        keyboard = create_inline_keyboard(buttons, columns=2)
        
        update.message.reply_text(
            text="👑 **پنل مدیریت جنگ جهانی باستان**\n\n"
            "لطفاً یکی از گزینه‌ها را انتخاب کنید:",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"خطا در admin_panel: {e}")
        update.message.reply_text("خطا در نمایش پنل مدیریت!")

def handle_admin_commands(update: Update, context: CallbackContext, data):
    """مدیریت دستورات ادمین"""
    try:
        query = update.callback_query
        
        if data == "admin_add_player":
            show_ai_countries_for_assignment(update, context)
        
        elif data == "admin_start_season":
            start_new_season(update, context)
        
        elif data == "admin_end_season":
            end_current_season(update, context)
        
        elif data == "admin_broadcast":
            context.user_data['awaiting_broadcast'] = True
            query.edit_message_text(
                text="لطفاً پیام عمومی خود را برای همه بازیکنان ارسال کنید:",
                parse_mode='Markdown'
            )
        
        elif data == "admin_reset_game":
            reset_game_confirmation(update, context)
        
        elif data == "admin_stats":
            show_admin_stats(update, context)
    
    except Exception as e:
        logger.error(f"خطا در handle_admin_commands: {e}")

def show_ai_countries_for_assignment(update: Update, context: CallbackContext):
    """نمایش لیست کشورهای AI برای اختصاص"""
    try:
        if not db:
            update.callback_query.message.reply_text("خطا در اتصال به پایگاه داده!")
            return
            
        ai_countries = db.get_ai_countries()
        
        if not ai_countries:
            update.callback_query.message.reply_text("❌ همه کشورها در اختیار بازیکنان هستند!")
            return
        
        buttons = []
        for country in ai_countries:
            buttons.append(
                InlineKeyboardButton(
                    text=f"{country['color']} {country['name']}",
                    callback_data=f"assign_country_{country['id']}"
                )
            )
        
        # اضافه کردن دکمه بازگشت
        buttons.append(InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel"))
        
        keyboard = create_inline_keyboard(buttons, columns=2)
        
        update.callback_query.edit_message_text(
            text="🤖 **کشورهای تحت کنترل AI:**\n\n"
            "لطفاً کشوری را برای اختصاص به بازیکن انتخاب کنید:",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"خطا در show_ai_countries_for_assignment: {e}")

def start_new_season(update: Update, context: CallbackContext):
    """شروع فصل جدید"""
    try:
        if not db:
            update.callback_query.message.reply_text("خطا در اتصال به پایگاه داده!")
            return
            
        # پیدا کردن شماره فصل بعدی
        cursor = db.conn.cursor()
        cursor.execute('SELECT MAX(season_number) as max_season FROM seasons')
        result = cursor.fetchone()
        next_season = (result['max_season'] or 0) + 1
        
        # شروع فصل جدید
        db.start_new_season(next_season)
        
        # ارسال پیام به کانال خبری (شبیه‌سازی)
        news_message = (
            f"🎉 **شروع فصل جدید جنگ‌های باستان!**\n\n"
            f"📅 فصل {next_season} آغاز شد!\n"
            f"⏰ تاریخ شروع: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            f"🌍 فرمانروایان، آماده نبرد شوید!\n"
            f"👑 برنده نهایی فصل {next_season} کیست؟\n\n"
            f"ساخته شده توسط @amele55\n"
            f"ورژن 2 ربات"
        )
        
        update.callback_query.message.reply_text(
            text=f"✅ فصل {next_season} با موفقیت آغاز شد!\n\n{news_message}",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"خطا در start_new_season: {e}")
        update.callback_query.message.reply_text("خطا در شروع فصل جدید!")

def end_current_season(update: Update, context: CallbackContext):
    """پایان فصل جاری"""
    try:
        if not db:
            update.callback_query.message.reply_text("خطا در اتصال به پایگاه داده!")
            return
            
        active_season = db.get_active_season()
        
        if not active_season:
            update.callback_query.message.reply_text("❌ هیچ فصلی فعال نیست!")
            return
        
        # پیدا کردن برنده (قدرتمندترین کشور انسانی)
        cursor = db.conn.cursor()
        cursor.execute('''
        SELECT c.id as country_id, c.name as country_name, 
               p.user_id as player_id, a.power
        FROM countries c
        JOIN players p ON c.id = p.country_id
        JOIN army a ON c.id = a.country_id
        WHERE c.controller = 'HUMAN'
        ORDER BY a.power DESC
        LIMIT 1
        ''')
        
        winner = cursor.fetchone()
        
        if winner:
            # به‌روزرسانی فصل
            cursor.execute('''
            UPDATE seasons 
            SET end_date = CURRENT_TIMESTAMP,
                winner_country_id = ?,
                winner_player_id = ?,
                is_active = 0
            WHERE id = ?
            ''', (winner['country_id'], winner['player_id'], active_season['id']))
            db.conn.commit()
            
            # پیام پایان فصل
            news_message = (
                f"🏆 **پایان فصل جنگ‌های باستان**\n\n"
                f"📅 فصل {active_season['season_number']} به پایان رسید!\n\n"
                f"👑 **فاتح نهایی جهان:**\n"
                f"🏛️ کشور: {winner['country_name']}\n"
                f"👤 بازیکن: {winner['player_id']}\n\n"
                f"ساخته شده توسط @amele55\n"
                f"منتظر فصل بعد باشید\n"
                f"ورژن 2 ربات"
            )
            
            update.callback_query.message.reply_text(
                text=f"✅ فصل {active_season['season_number']} با موفقیت پایان یافت!\n\n{news_message}",
                parse_mode='Markdown'
            )
        else:
            update.callback_query.message.reply_text("❌ هیچ بازیکن انسانی برای انتخاب برنده وجود ندارد!")
    except Exception as e:
        logger.error(f"خطا در end_current_season: {e}")
        update.callback_query.message.reply_text("خطا در پایان فصل!")

def reset_game_confirmation(update: Update, context: CallbackContext):
    """تأیید ریست بازی"""
    try:
        buttons = [
            InlineKeyboardButton("✅ بله، ریست کن", callback_data="admin_confirm_reset"),
            InlineKeyboardButton("❌ خیر، لغو", callback_data="admin_panel"),
        ]
        
        keyboard = InlineKeyboardMarkup([buttons])
        
        update.callback_query.edit_message_text(
            text="⚠️ **هشدار: ریست کامل بازی**\n\n"
            "آیا مطمئن هستید که می‌خواهید کل بازی را ریست کنید؟\n"
            "❗ این عمل غیرقابل بازگشت است و همه داده‌ها پاک می‌شوند!",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"خطا در reset_game_confirmation: {e}")

def show_admin_stats(update: Update, context: CallbackContext):
    """نمایش آمار مدیریت"""
    try:
        if not db:
            update.callback_query.message.reply_text("خطا در اتصال به پایگاه داده!")
            return
            
        cursor = db.conn.cursor()
        
        # تعداد بازیکنان
        cursor.execute('SELECT COUNT(*) as count FROM players WHERE is_active = 1')
        player_count = cursor.fetchone()['count']
        
        # تعداد کشورها
        cursor.execute('SELECT COUNT(*) as count FROM countries WHERE is_active = 1')
        country_count = cursor.fetchone()['count']
        
        # تعداد AI
        cursor.execute('SELECT COUNT(*) as count FROM countries WHERE controller = "AI" AND is_active = 1')
        ai_count = cursor.fetchone()['count']
        
        # تعداد HUMAN
        cursor.execute('SELECT COUNT(*) as count FROM countries WHERE controller = "HUMAN" AND is_active = 1')
        human_count = cursor.fetchone()['count']
        
        # فصل فعال
        active_season = db.get_active_season()
        season_info = f"فصل {active_season['season_number']}" if active_season else "هیچ فصل فعالی"
        
        stats_text = (
            f"📊 **آمار مدیریت جنگ جهانی باستان**\n\n"
            f"👥 بازیکنان انسانی: {player_count}\n"
            f"🌍 کل کشورها: {country_count}\n"
            f"🤖 کشورهای AI: {ai_count}\n"
            f"👤 کشورهای انسانی: {human_count}\n"
            f"📅 وضعیت فصل: {season_info}\n\n"
            f"🔄 آخرین به‌روزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        update.callback_query.edit_message_text(
            text=stats_text,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"خطا در show_admin_stats: {e}")
        update.callback_query.message.reply_text("خطا در نمایش آمار!")

def handle_message(update: Update, context: CallbackContext):
    """مدیریت پیام‌های متنی"""
    try:
        user_id = update.effective_user.id
        text = update.message.text
        
        # بررسی اگر مالک در حال ارسال آدی بازیکن است
        if user_id == OWNER_ID and 'selected_country' in context.user_data:
            try:
                target_user_id = int(text)
                country_id = context.user_data['selected_country']
                
                if not db:
                    update.message.reply_text("خطا در اتصال به پایگاه داده!")
                    return
                
                # اختصاص کشور به بازیکن
                try:
                    # در نسخه 13.15 نمی‌توانیم از await استفاده کنیم
                    # یک راه ساده‌تر
                    success = db.assign_country_to_player(
                        country_id,
                        target_user_id,
                        f"user_{target_user_id}",  # username موقت
                        f"Player_{target_user_id}"  # full_name موقت
                    )
                    
                    if success:
                        update.message.reply_text(
                            text=f"✅ کشور با موفقیت به بازیکن اختصاص داده شد!\n"
                            f"🆔 آیدی بازیکن: {target_user_id}\n\n"
                            f"به بازیکن بگویید از دستور /start استفاده کند."
                        )
                    else:
                        update.message.reply_text("❌ خطا در اختصاص کشور!")
                    
                    # پاک کردن حالت
                    del context.user_data['selected_country']
                    
                except Exception as e:
                    update.message.reply_text(f"❌ خطا در دریافت اطلاعات کاربر: {str(e)}")
                
            except ValueError:
                update.message.reply_text("❌ لطفاً یک آیدی عددی معتبر وارد کنید!")
            except Exception as e:
                update.message.reply_text(f"❌ خطا: {str(e)}")
        
        # بررسی اگر مالک در حال ارسال پیام عمومی است
        elif user_id == OWNER_ID and context.user_data.get('awaiting_broadcast'):
            # ارسال پیام به همه بازیکنان
            if db:
                players = db.get_all_players()
                
                success_count = 0
                for player in players:
                    try:
                        context.bot.send_message(
                            chat_id=player['user_id'],
                            text=f"📢 **پیام عمومی از مدیریت:**\n\n{text}"
                        )
                        success_count += 1
                    except:
                        pass
                
                update.message.reply_text(
                    text=f"✅ پیام به {success_count} بازیکن ارسال شد."
                )
            else:
                update.message.reply_text("خطا در اتصال به پایگاه داده!")
            
            # پاک کردن حالت
            context.user_data['awaiting_broadcast'] = False
        
        else:
            # پاسخ به پیام‌های دیگر
            update.message.reply_text(
                text="برای دسترسی به منوی بازی از /start استفاده کنید.\n"
                "برای مدیریت (مالک) از /admin استفاده کنید."
            )
    
    except Exception as e:
        logger.error(f"خطا در handle_message: {e}")
        update.message.reply_text("خطا در پردازش پیام!")

def ai_scheduler():
    """زمان‌بند برای اجرای خودکار AI"""
    scheduler = BackgroundScheduler()
    
    def process_ai_decisions():
        try:
            if game:
                decisions = game.process_all_ai_decisions()
                if decisions:
                    logger.info(f"AI decisions processed: {len(decisions)}")
        except Exception as e:
            logger.error(f"Error in AI scheduler: {e}")
    
    # اجرای هر 5 دقیقه
    scheduler.add_job(process_ai_decisions, 'interval', minutes=5)
    scheduler.start()
    
    return scheduler

def setup_updater():
    """تنظیم و راه‌اندازی updater"""
    updater_instance = Updater(token=BOT_TOKEN, use_context=True)
    dp = updater_instance.dispatcher
    
    # اضافه کردن هندلرهای دستورات
    dp.add_handler(CommandHandler("start", start_command))
    dp.add_handler(CommandHandler("admin", admin_panel))
    
    # اضافه کردن هندلرهای دکمه‌ها
    dp.add_handler(CallbackQueryHandler(button_callback_handler))
    
    # اضافه کردن هندلر پیام‌های متنی
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    
    return updater_instance

@app.route('/')
def home():
    return "🤖 Ancient War Bot v2 is running on Python 3.13 with python-telegram-bot 13.15!"

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook endpoint برای تلگرام"""
    global updater
    
    if request.headers.get('content-type') == 'application/json':
        json_str = request.get_data().decode('UTF-8')
        update = Update.de_json(json_str, updater.bot)
        updater.dispatcher.process_update(update)
        return 'OK'
    return 'Bad Request', 400

def main():
    """تابع اصلی اجرای ربات"""
    global updater
    
    # راه‌اندازی AI Scheduler
    scheduler = ai_scheduler()
    
    # راه‌اندازی updater
    updater = setup_updater()
    
    if WEBHOOK_URL and WEBHOOK_URL.strip():
        # حالت Webhook (برای Render)
        logger.info(f"Starting in Webhook mode with URL: {WEBHOOK_URL}")
        
        # تنظیم Webhook
        updater.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
        
        # اجرای Flask app
        app.run(host=LISTEN, port=PORT)
    else:
        # حالت Polling (برای توسعه)
        logger.info("Starting in Polling mode...")
        updater.start_polling()
        updater.idle()
    
    # توقف زمان‌بند
    scheduler.shutdown()

if __name__ == '__main__':
    main()
