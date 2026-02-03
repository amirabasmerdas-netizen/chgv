import random
from database import Database

class Advisor:
    def __init__(self):
        self.db = Database()
        self.advice_types = [
            "RESOURCE",
            "ARMY",
            "DIPLOMACY",
            "WARNING",
            "STRATEGY"
        ]
    
    def generate_advice(self, country_id):
        """تولید مشاوره برای کشور مشخص"""
        country = self.db.get_country_by_id(country_id)
        resources = self.db.get_country_resources(country_id)
        army = self.db.get_country_army(country_id)
        
        if not country or not resources or not army:
            return "هنوز اطلاعات کافی برای مشاوره وجود ندارد."
        
        advice_type = random.choice(self.advice_types)
        
        if advice_type == "RESOURCE":
            return self._resource_advice(country, resources)
        elif advice_type == "ARMY":
            return self._army_advice(country, army, resources)
        elif advice_type == "DIPLOMACY":
            return self._diplomacy_advice(country_id)
        elif advice_type == "WARNING":
            return self._warning_advice(country_id)
        else:
            return self._strategy_advice(country, army)
    
    def _resource_advice(self, country, resources):
        """مشاوره منابع"""
        if resources['food'] < 300:
            return f"🤔 **وزیر**: غذای {country['name']} در حال اتمام است! روی تولید غذا تمرکز کن."
        elif resources['gold'] < 200:
            return f"💰 **وزیر**: خزانه طلای {country['name']} خالی است. معادن طلا را فعال کن."
        elif resources['iron'] < 100:
            return f"⚒️ **وزیر**: آهن برای ارتقا ارتش ضروری است. معادن آهن را توسعه بده."
        else:
            return f"📊 **وزیر**: منابع {country['name']} در وضعیت خوبی است. می‌توانی روی توسعه تمرکز کنی."
    
    def _army_advice(self, country, army, resources):
        """مشاوره ارتش"""
        if army['level'] < 3:
            return f"⚔️ **وزیر**: ارتش {country['name']} نیاز به ارتقا دارد. سطح {army['level']} ضعیف است."
        elif army['infantry'] < 150:
            return f"🛡️ **وزیر**: پیاده‌نظام {country['name']} کم است. سربازان بیشتری آموزش بده."
        elif resources['gold'] > 500 and army['power'] < 300:
            return f"👑 **وزیر**: طلای کافی داری! ارتش {country['name']} را ارتقا بده."
        else:
            return f"🎖️ **وزیر**: ارتش {country['name']} آماده نبرد است. از قدرتت استفاده کن."
    
    def _diplomacy_advice(self, country_id):
        """مشاوره دیپلماسی"""
        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT COUNT(*) as alliance_count 
        FROM alliances 
        WHERE (country1_id = ? OR country2_id = ?) 
          AND relation_type = 'ALLIANCE'
        ''', (country_id, country_id))
        
        result = cursor.fetchone()
        alliance_count = result['alliance_count'] if result else 0
        
        if alliance_count == 0:
            return f"🤝 **وزیر**: {self._get_country_name(country_id)} هیچ متحدی ندارد! اتحاد تشکیل بده."
        elif alliance_count < 2:
            return f"👥 **وزیر**: فقط {alliance_count} متحد داری. اتحادهای بیشتری ایجاد کن."
        else:
            return f"🎯 **وزیر**: {alliance_count} اتحاد داری. حالا روی دشمنان تمرکز کن."
    
    def _warning_advice(self, country_id):
        """هشدارهای استراتژیک"""
        cursor = self.db.conn.cursor()
        
        # پیدا کردن دشمنان قوی
        cursor.execute('''
        SELECT c.name, a.power 
        FROM alliances al
        JOIN countries c ON 
            (c.id = al.country2_id AND al.country1_id = ?) OR
            (c.id = al.country1_id AND al.country2_id = ?)
        JOIN army a ON a.country_id = c.id
        WHERE al.relation_type = 'WAR'
        ORDER BY a.power DESC
        LIMIT 1
        ''', (country_id, country_id))
        
        strong_enemy = cursor.fetchone()
        
        if strong_enemy:
            return f"⚠️ **وزیر**: هشدار! {strong_enemy['name']} با قدرت {strong_enemy['power']} تهدید می‌کند."
        
        # پیدا کردن کشورهای ضعیف برای حمله
        cursor.execute('''
        SELECT c.name, a.power 
        FROM countries c
        JOIN army a ON a.country_id = c.id
        WHERE c.controller = 'HUMAN' 
          AND c.id != ?
          AND a.power < (SELECT power FROM army WHERE country_id = ?) * 0.7
        LIMIT 1
        ''', (country_id, country_id))
        
        weak_target = cursor.fetchone()
        
        if weak_target:
            return f"🎯 **وزیر**: فرصت! {weak_target['name']} با قدرت {weak_target['power']} هدف خوبی است."
        
        return "🔍 **وزیر**: وضعیت فعلی امن است. به توسعه کشورت ادامه بده."
    
    def _strategy_advice(self, country, army):
        """مشاوره استراتژیک"""
        strategies = [
            f"🏹 **وزیر**: از تخصص {country['specialty']} {country['name']} بیشتر استفاده کن.",
            f"🗺️ **وزیر**: نقشه بزرگ را ببین! توسعه پایدار بهتر از جنگ‌های پیاپی است.",
            f"⚡ **وزیر**: سرعت عمل کلید پیروزی است. فرصت‌ها را از دست نده.",
            f"👑 **وزیر**: به عنوان فرمانروای {country['name']}، تصمیمات دوراندیشانه بگیر.",
            f"🛡️ **وزیر**: دفاع قوی به اندازه حمله مهم است. دیوارهایت را مستحکم کن."
        ]
        return random.choice(strategies)
    
    def _get_country_name(self, country_id):
        country = self.db.get_country_by_id(country_id)
        return country['name'] if country else "کشور"
    
    def send_advice_to_player(self, user_id):
        """ارسال مشاوره به بازیکن"""
        player_country = self.db.get_player_country(user_id)
        if player_country:
            advice = self.generate_advice(player_country['id'])
            return advice
        return None
