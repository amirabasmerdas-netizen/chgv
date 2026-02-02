import random
from datetime import datetime
from database import Database
from config import COUNTRIES

class GameLogic:
    def __init__(self):
        self.db = Database()
    
    def ai_decision_maker(self, ai_country_code):
        """تصمیم‌گیری هوش مصنوعی"""
        country_info = self.db.get_country_info(ai_country_code)
        
        if not country_info:
            return
        
        decisions = []
        
        # 1. تصمیم درباره ارتقا ارتش (30% احتمال)
        if random.random() < 0.3 and country_info['gold'] > 200:
            success, message = self.db.upgrade_army(ai_country_code)
            if success:
                decisions.append(f"🤖 {country_info['name']} ارتش خود را ارتقا داد")
        
        # 2. تصمیم درباره حمله (25% احتمال)
        if random.random() < 0.25:
            target = self.select_attack_target(ai_country_code)
            if target:
                success = self.simulate_battle(ai_country_code, target)
                if success:
                    decisions.append(f"⚔️ {country_info['name']} به {target} حمله کرد و پیروز شد")
                else:
                    decisions.append(f"⚔️ {country_info['name']} به {target} حمله کرد و شکست خورد")
        
        # 3. تصمیم درباره اتحاد (15% احتمال)
        if random.random() < 0.15:
            ally = self.select_ally(ai_country_code)
            if ally:
                success, message = self.db.create_alliance(ai_country_code, ally)
                if success:
                    ally_info = self.db.get_country_info(ally)
                    decisions.append(f"🤝 {country_info['name']} با {ally_info['name']} اتحاد تشکیل داد")
        
        return decisions
    
    def select_attack_target(self, attacker_code):
        """انتخاب هدف برای حمله"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # دریافت همه کشورهای دیگر
        cursor.execute('''
            SELECT code, name, power_score FROM countries 
            WHERE code != ? AND controller_type = 'HUMAN'
            ORDER BY power_score
        ''', (attacker_code,))
        
        targets = cursor.fetchall()
        conn.close()
        
        if not targets:
            return None
        
        # انتخاب هدف ضعیف‌تر (احتمال بیشتر)
        weights = [1/(i+1) for i in range(len(targets))]
        total = sum(weights)
        probabilities = [w/total for w in weights]
        
        selected = random.choices(targets, weights=probabilities, k=1)[0]
        return selected[0]
    
    def select_ally(self, country_code):
        """انتخاب متحد"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # دریافت کشورهای دیگر که در اتحاد نیستند
        cursor.execute('''
            SELECT c.code FROM countries c
            WHERE c.code != ? 
            AND c.code NOT IN (
                SELECT a.country2_code FROM alliances a 
                WHERE a.country1_code = ? AND a.is_active = 1
                UNION
                SELECT a.country1_code FROM alliances a 
                WHERE a.country2_code = ? AND a.is_active = 1
            )
            ORDER BY RANDOM()
            LIMIT 3
        ''', (country_code, country_code, country_code))
        
        allies = cursor.fetchall()
        conn.close()
        
        if allies:
            return allies[0][0]
        return None
    
    def simulate_battle(self, attacker, defender):
        """شبیه‌سازی نبرد"""
        attacker_info = self.db.get_country_info(attacker)
        defender_info = self.db.get_country_info(defender)
        
        if not attacker_info or not defender_info:
            return False
        
        # محاسبه شانس برنده
        attacker_power = attacker_info.get('total_power', 100)
        defender_power = defender_info.get('total_power', 100)
        
        # تصادفی بودن نتیجه
        attacker_luck = random.uniform(0.8, 1.2)
        defender_luck = random.uniform(0.8, 1.2)
        
        final_attacker = attacker_power * attacker_luck
        final_defender = defender_power * defender_luck
        
        attacker_wins = final_attacker > final_defender
        
        # ثبت رویداد
        if attacker_wins:
            # انتقال منابع به مهاجم
            self.db.update_resources(attacker, 
                                   gold_change=random.randint(100, 500),
                                   iron_change=random.randint(50, 200))
            self.db.update_resources(defender,
                                   gold_change=-random.randint(100, 300),
                                   iron_change=-random.randint(30, 100))
        
        return attacker_wins
    
    def calculate_winner(self):
        """محاسبه برنده فصل"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # پیدا کردن قوی‌ترین بازیکن انسانی
        cursor.execute('''
            SELECT c.code, c.player_id, c.power_score, p.username 
            FROM countries c
            JOIN players p ON c.player_id = p.user_id
            WHERE c.controller_type = 'HUMAN'
            ORDER BY c.power_score DESC
            LIMIT 1
        ''')
        
        winner = cursor.fetchone()
        conn.close()
        
        if winner:
            return {
                'country_code': winner[0],
                'player_id': winner[1],
                'power_score': winner[2],
                'username': winner[3]
            }
        
        return None
    
    def generate_resources(self):
        """تولید منابع خودکار برای همه کشورها"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # تولید منابع برای همه کشورها
        cursor.execute('''
            UPDATE countries 
            SET gold = gold + CAST(RANDOM() * 50 + 10 AS INTEGER),
                iron = iron + CAST(RANDOM() * 30 + 5 AS INTEGER),
                stone = stone + CAST(RANDOM() * 30 + 5 AS INTEGER),
                food = food + CAST(RANDOM() * 100 + 20 AS INTEGER),
                power_score = (
                    SELECT (total_power/10) + (gold/100) + (iron/50) + (stone/50) 
                    FROM army 
                    WHERE army.country_code = countries.code
                ),
                last_update = ?
        ''', (datetime.now().isoformat(),))
        
        conn.commit()
        
        # دریافت کشورهای AI
        cursor.execute('SELECT code FROM countries WHERE controller_type = "AI"')
        ai_countries = cursor.fetchall()
        
        conn.close()
        
        # تصمیم‌گیری AI
        all_decisions = []
        for ai_country in ai_countries:
            decisions = self.ai_decision_maker(ai_country[0])
            if decisions:
                all_decisions.extend(decisions)
        
        return all_decisions
