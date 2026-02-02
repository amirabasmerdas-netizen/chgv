# تنظیمات ربات
import os
from dotenv import load_dotenv

load_dotenv()

# تنظیمات ربات
BOT_TOKEN = os.getenv('BOT_TOKEN')
OWNER_ID = 8588773170  # آیدی مالک
CHANNEL_ID = os.getenv('CHANNEL_ID', '')  # آیدی کانال خبری
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
PORT = int(os.getenv('PORT', 5000))

# کشورهای موجود در بازی
COUNTRIES = {
    'persia': {'name': 'امپراتوری پارس', 'specialty': 'سواره نظام سریع'},
    'rome': {'name': 'امپراتوری روم', 'specialty': 'دفاع قلعه'},
    'egypt': {'name': 'فراعنه مصر', 'specialty': 'زراعت و منابع'},
    'china': {'name': 'امپراتوری چین', 'specialty': 'تعداد زیاد سرباز'},
    'greece': {'name': 'یونان باستان', 'specialty': 'فالانژهای قدرتمند'},
    'babylon': {'name': 'بابل', 'specialty': 'دیپلماسی و دانش'},
    'assyr': {'name': 'آشور', 'specialty': 'حمله سریع'},
    'carthage': {'name': 'کارتاژ', 'specialty': 'نیروی دریایی'},
    'india': {'name': 'امپراتوری هند', 'specialty': 'فیل‌های جنگی'},
    'macedonia': {'name': 'مقدونیه', 'specialty': 'ارتش سازمان‌یافته'},
    'hittite': {'name': 'هیتی', 'specialty': 'سلاح‌های آهنی'},
    'phoenicia': {'name': 'فینیقیه', 'specialty': 'تجارت و ثروت'},
}

# سطح‌های ارتش
ARMY_LEVELS = {
    1: {'power': 10, 'speed': 5, 'defense': 5, 'upgrade_cost': 100},
    2: {'power': 20, 'speed': 8, 'defense': 10, 'upgrade_cost': 200},
    3: {'power': 35, 'speed': 12, 'defense': 18, 'upgrade_cost': 350},
    4: {'power': 55, 'speed': 17, 'defense': 30, 'upgrade_cost': 550},
    5: {'power': 80, 'speed': 23, 'defense': 45, 'upgrade_cost': 800},
}
