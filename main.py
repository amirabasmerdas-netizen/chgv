import os

# توکن ربات تلگرام (از متغیر محیطی بگیر یا مستقیماً قرار بده)
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# تنظیمات مالک
OWNER_ID = 8588773170

# تنظیمات Webhook
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
PORT = int(os.getenv("PORT", 8443))
LISTEN = "0.0.0.0"

# تنظیمات دیتابیس
DB_NAME = "ancient_war.db"

# لیست کشورهای باستانی
ANCIENT_COUNTRIES = [
    {"id": 1, "name": "پارس", "specialty": "اسب‌سوار سریع", "color": "🟡"},
    {"id": 2, "name": "روم", "specialty": "دفاع قلعه", "color": "🟥"},
    {"id": 3, "name": "مصر", "specialty": "تیرانداز ماهر", "color": "🟦"},
    {"id": 4, "name": "چین", "specialty": "نیروی انبوه", "color": "🟢"},
    {"id": 5, "name": "یونان", "specialty": "فالانژ قدرتمند", "color": "🟣"},
    {"id": 6, "name": "بابل", "specialty": "دیوار مستحکم", "color": "🟠"},
    {"id": 7, "name": "آشور", "specialty": "ارابه جنگی", "color": "🟤"},
    {"id": 8, "name": "کارتاژ", "specialty": "ناوبری دریایی", "color": "🔵"},
    {"id": 9, "name": "هند", "specialty": "فیل جنگی", "color": "🟣"},
    {"id": 10, "name": "مقدونیه", "specialty": "سواره‌نظام", "color": "🔴"}
]

# منابع اولیه
INITIAL_RESOURCES = {
    "gold": 1000,
    "iron": 500,
    "stone": 800,
    "food": 1200
}

# ارتش اولیه
INITIAL_ARMY = {
    "level": 1,
    "infantry": 100,
    "cavalry": 20,
    "archers": 30,
    "defense": 50,
    "power": 150
}

# تنظیمات فصل
SEASON_DURATION_DAYS = 30  # مدت فصل به روز
