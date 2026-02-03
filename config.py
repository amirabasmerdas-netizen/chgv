import os
from dotenv import load_dotenv

load_dotenv()

# تنظیمات اصلی ربات
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
OWNER_ID = 8588773170  # آیدی مالک ربات
CHANNEL_ID = os.getenv('CHANNEL_ID', '@ancientwarnews')  # کانال خبری
WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
PORT = int(os.getenv('PORT', 10000))

# کشورهای بازی
COUNTRIES = {
    'persia': {
        'name': 'امپراتوری پارس',
        'specialty': 'سواره نظام سریع',
        'color': '#FF6B35',
        'start_gold': 1200,
        'start_army': 150
    },
    'rome': {
        'name': 'امپراتوری روم',
        'specialty': 'دفاع قلعه',
        'color': '#004E89',
        'start_gold': 1100,
        'start_army': 140
    },
    'egypt': {
        'name': 'فراعنه مصر',
        'specialty': 'زراعت و منابع',
        'color': '#FFC107',
        'start_gold': 1300,
        'start_army': 120
    },
    'china': {
        'name': 'امپراتوری چین',
        'specialty': 'تعداد زیاد سرباز',
        'color': '#D32F2F',
        'start_gold': 1000,
        'start_army': 200
    },
    'greece': {
        'name': 'یونان باستان',
        'specialty': 'فالانژهای قدرتمند',
        'color': '#2196F3',
        'start_gold': 1150,
        'start_army': 130
    },
    'babylon': {
        'name': 'بابل',
        'specialty': 'دیپلماسی و دانش',
        'color': '#9C27B0',
        'start_gold': 1250,
        'start_army': 110
    },
    'assyr': {
        'name': 'آشور',
        'specialty': 'حمله سریع',
        'color': '#795548',
        'start_gold': 1050,
        'start_army': 160
    },
    'carthage': {
        'name': 'کارتاژ',
        'specialty': 'نیروی دریایی',
        'color': '#388E3C',
        'start_gold': 1150,
        'start_army': 125
    },
    'india': {
        'name': 'امپراتوری هند',
        'specialty': 'فیل‌های جنگی',
        'color': '#FF9800',
        'start_gold': 1200,
        'start_army': 135
    },
    'macedonia': {
        'name': 'مقدونیه',
        'specialty': 'ارتش سازمان‌یافته',
        'color': '#607D8B',
        'start_gold': 1100,
        'start_army': 145
    },
}

# سطح‌های ارتش
ARMY_LEVELS = {
    1: {'name': 'تازه‌کار', 'power': 100, 'cost': 0, 'upgrade_cost': 500},
    2: {'name': 'ماهر', 'power': 250, 'cost': 500, 'upgrade_cost': 1000},
    3: {'name': 'حرفه‌ای', 'power': 500, 'cost': 1500, 'upgrade_cost': 2000},
    4: {'name': 'استاد', 'power': 850, 'cost': 3500, 'upgrade_cost': 3500},
    5: {'name': 'افسانه', 'power': 1300, 'cost': 7000, 'upgrade_cost': 0},
}

# انواع ساختمان‌ها
BUILDINGS = {
    'mine': {'name': 'معدن طلا', 'cost': 300, 'production': 50},
    'forge': {'name': 'کارگاه آهنگری', 'cost': 200, 'production': 30},
    'quarry': {'name': 'معدن سنگ', 'cost': 150, 'production': 20},
    'farm': {'name': 'مزرعه', 'cost': 100, 'production': 100},
    'barracks': {'name': 'پادگان', 'cost': 400, 'capacity': 100},
    'stable': {'name': 'اصطبل', 'cost': 600, 'capacity': 50},
    'wall': {'name': 'دیوار دفاعی', 'cost': 800, 'defense': 200},
}

# رویدادهای تصادفی
RANDOM_EVENTS = [
    {'name': 'کشف معدن', 'effect': {'gold': 500}, 'probability': 0.1},
    {'name': 'قحطی', 'effect': {'food': -300}, 'probability': 0.05},
    {'name': 'شورش', 'effect': {'soldiers': -50}, 'probability': 0.07},
    {'name': 'معجزه', 'effect': {'all': 200}, 'probability': 0.03},
    {'name': 'حمله دزدان', 'effect': {'gold': -200}, 'probability': 0.08},
]
