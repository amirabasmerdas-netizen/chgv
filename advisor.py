import random
from datetime import datetime
from database import Database

class Advisor:
    def __init__(self):
        self.db = Database()
    
    def generate_advice(self, country_code):
        """تولید پیام مشاوره برای بازیکن"""
        country_info = self.db.get_country_info(country_code)
        
        if not country_info:
            return None
        
        # تولید پیام بر اساس تحلیل
        messages = []
        
        # 1. پیام درباره منابع
        if country_info['gold'] < 200:
            messages.append("طلای شما کم است! معادن طلا را توسعه دهید.")
        
        if country_info['food'] < 300:
            messages.append("ذخایر غذایی شما در حال اتمام است. کشاورزی را تقویت کنید.")
        
        # 2. پیام درباره ارتش
        if country_info.get('army_level', 1) < 2:
            messages.append("ارتش شما نیاز به ارتقا دارد. آن را تقویت کنید!")
        elif country_info.get('total_power', 0) < 300:
            messages.append("قدرت ارتش شما پایین است. سربازان بیشتری استخدام کنید.")
        
        # 3. پیام درباره اتحادها
        alliances = self.get_alliances(country_code)
        if len(alliances) == 0:
            messages.append("شما هیچ متحدی ندارید. برای بقا به اتحاد فکر کنید.")
        
        # 4. پیام خطرات احتمالی
        threats = self.detect_threats(country_code)
        if threats:
            messages.append(f"کشور {threats} ممکن است به شما حمله کند. آماده باشید!")
        
        # 5. پیام فرصت‌ها
        opportunities = self.find_opportunities(country_code)
        if opportunities:
            messages.append(f"کشور {opportunities} ضعیف است. حمله را در نظر بگیرید.")
        
        # انتخاب یک پیام تصادفی اگر چندین پیام وجود دارد
        if messages:
            message = random.choice(messages)
            return {
                'message': f"وزیر شما می‌گوید: {message}",
                'priority': 'HIGH' if 'حمله' in message or 'ضعیف' in message else 'NORMAL'
            }
        
        return None
    
    def analyze_situation(self, country_info):
        """تحلیل وضعیت کشور"""
        analysis = {
            'resource_status': 'GOOD',
            'military_status': 'AVERAGE',
            'diplomatic_status': 'NEUTRAL'
        }
        
        # تحلیل منابع
        gold = country_info.get('gold', 0)
        food = country_info.get('food', 0)
        
        if gold < 100 or food < 200:
            analysis['resource_status'] = 'CRITICAL'
        elif gold < 300 or food < 500:
            analysis['resource_status'] = 'LOW'
        elif gold > 1000 and food > 1000:
            analysis['resource_status'] = 'EXCELLENT'
        
        # تحلیل نظامی
        total_power = country_info.get('total_power', 0)
        if total_power < 150:
            analysis['military_status'] = 'WEAK'
        elif total_power > 500:
            analysis['military_status'] = 'STRONG'
        
        return analysis
    
    def get_alliances(self, country_code):
        """دریافت لیست اتحادها"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.name FROM alliances a
            JOIN countries c ON (
                (a.country1_code = c.code AND a.country2_code = ?) 
                OR (a.country2_code = c.code AND a.country1_code = ?)
            )
            WHERE a.is_active = 1 AND c.code != ?
        ''', (country_code, country_code, country_code))
        
        alliances = [row[0] for row in cursor.fetchall()]
        conn.close()
        return alliances
    
    def detect_threats(self, country_code):
        """تشخیص تهدیدات"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # قدرت کشور فعلی
        cursor.execute('SELECT power_score FROM countries WHERE code = ?', (country_code,))
        current_power = cursor.fetchone()
        current_power = current_power[0] if current_power else 0
        
        # کشورهای قوی‌تر که اتحاد ندارند
        cursor.execute('''
            SELECT c.name FROM countries c
            WHERE c.controller_type = 'AI' 
            AND c.power_score > ?
            AND c.code NOT IN (
                SELECT a.country2_code FROM alliances a 
                WHERE a.country1_code = ? AND a.is_active = 1
                UNION
                SELECT a.country1_code FROM alliances a 
                WHERE a.country2_code = ? AND a.is_active = 1
            )
            ORDER BY RANDOM()
            LIMIT 1
        ''', (current_power, country_code, country_code))
        
        threat = cursor.fetchone()
        conn.close()
        
        return threat[0] if threat else None
    
    def find_opportunities(self, country_code):
        """پیدا کردن فرصت‌ها"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # قدرت کشور فعلی
        cursor.execute('SELECT power_score FROM countries WHERE code = ?', (country_code,))
        current_power = cursor.fetchone()
        current_power = current_power[0] if current_power else 0
        
        # کشورهای ضعیف‌تر
        cursor.execute('''
            SELECT c.name FROM countries c
            WHERE c.controller_type = 'AI' 
            AND c.power_score < ?
            ORDER BY c.power_score ASC
            LIMIT 1
        ''', (current_power * 0.7,))
        
        opportunity = cursor.fetchone()
        conn.close()
        
        return opportunity[0] if opportunity else None
    
    def save_advice_message(self, country_code, message):
        """ذخیره پیام وزیر"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO advisor_messages (country_code, message_type, message, created_date)
            VALUES (?, 'ADVICE', ?, ?)
        ''', (country_code, message, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
