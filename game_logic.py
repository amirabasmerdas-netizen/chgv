import random
import logging
from datetime import datetime, timedelta
from database import Database

logger = logging.getLogger(__name__)

class GameLogic:
    def __init__(self):
        self.db = Database()
    
    def ai_decision_maker(self, ai_country_id):
        """تصمیم‌گیری AI برای کشور مشخص"""
        decisions = []
        
        # منابع AI
        resources = self.db.get_country_resources(ai_country_id)
        army = self.db.get_country_army(ai_country_id)
        
        # تصمیم‌های احتمالی AI
        actions = [
            self._ai_collect_resources,
            self._ai_train_army,
            self._ai_attack_decision,
            self._ai_form_alliance,
            self._ai_betray_alliance
        ]
        
        # اجرای 1-2 تصمیم تصادفی
        num_actions = random.randint(1, 2)
        selected_actions = random.sample(actions, num_actions)
        
        for action in selected_actions:
            try:
                decision = action(ai_country_id, resources, army)
                if decision:
                    decisions.append(decision)
            except Exception as e:
                logger.error(f"Error in AI action: {e}")
        
        return decisions
    
    def _ai_collect_resources(self, country_id, resources, army):
        """AI منابع جمع‌آوری می‌کند"""
        if resources['food'] < 500:
            food_gain = random.randint(100, 300)
            self.db.update_resources(country_id, {'food': food_gain})
            return f"AI جمع‌آوری غذا: +{food_gain}"
        
        if resources['gold'] < 300:
            gold_gain = random.randint(50, 150)
            self.db.update_resources(country_id, {'gold': gold_gain})
            return f"AI جمع‌آوری طلا: +{gold_gain}"
        
        return None
    
    def _ai_train_army(self, country_id, resources, army):
        """AI ارتش آموزش می‌دهد"""
        if (resources['gold'] > 200 and resources['food'] > 300 and 
            army['level'] < 5):
            
            # افزایش نیروها
            infantry_gain = random.randint(10, 30)
            self.db.update_resources(country_id, {
                'gold': -100,
                'food': -150,
                'iron': -50
            })
            
            cursor = self.db.conn.cursor()
            cursor.execute('''
            UPDATE army 
            SET infantry = infantry + ?
            WHERE country_id = ?
            ''', (infantry_gain, country_id))
            self.db.conn.commit()
            
            return f"AI آموزش ارتش: +{infantry_gain} پیاده‌نظام"
        return None
    
    def _ai_attack_decision(self, country_id, resources, army):
        """تصمیم حمله AI"""
        # پیدا کردن کشورهای ضعیف‌تر
        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT a.country_id, a.power, c.name 
        FROM army a
        JOIN countries c ON a.country_id = c.id
        WHERE c.controller = 'HUMAN' 
          AND a.power < ? 
          AND c.id != ?
        ORDER BY a.power ASC
        LIMIT 3
        ''', (army['power'] * 1.2, country_id))
        
        weak_countries = cursor.fetchall()
        
        if weak_countries and army['power'] > 200:
            target = random.choice(weak_countries)
            
            # ثبت حمله در رویدادها
            cursor.execute('''
            INSERT INTO events (event_type, country_id, target_country_id, description)
            VALUES (?, ?, ?, ?)
            ''', ('AI_ATTACK', country_id, target['country_id'], 
                  f"حمله AI به {target['name']}"))
            self.db.conn.commit()
            
            return f"AI حمله به {target['name']}"
        return None
    
    def _ai_form_alliance(self, country_id, resources, army):
        """تشکیل اتحاد توسط AI"""
        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT c.id, c.name 
        FROM countries c
        LEFT JOIN alliances a ON 
            (a.country1_id = ? AND a.country2_id = c.id) OR
            (a.country2_id = ? AND a.country1_id = c.id)
        WHERE c.controller = 'AI' 
          AND c.id != ?
          AND a.id IS NULL
        LIMIT 2
        ''', (country_id, country_id, country_id))
        
        possible_allies = cursor.fetchall()
        
        if possible_allies:
            ally = random.choice(possible_allies)
            
            # اگر منابع کافی داریم، اتحاد تشکیل بده
            if resources['gold'] > 500:
                cursor.execute('''
                INSERT INTO alliances (country1_id, country2_id, relation_type)
                VALUES (?, ?, 'ALLIANCE')
                ''', (min(country_id, ally['id']), max(country_id, ally['id'])))
                self.db.conn.commit()
                
                return f"AI تشکیل اتحاد با {ally['name']}"
        return None
    
    def _ai_betray_alliance(self, country_id, resources, army):
        """خیانت AI به اتحاد"""
        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT c.id, c.name 
        FROM alliances a
        JOIN countries c ON 
            (c.id = a.country2_id AND a.country1_id = ?) OR
            (c.id = a.country1_id AND a.country2_id = ?)
        WHERE a.relation_type = 'ALLIANCE'
        ''', (country_id, country_id))
        
        allies = cursor.fetchall()
        
        if allies and random.random() < 0.1:  # 10% احتمال خیانت
            traitor = random.choice(allies)
            
            # تغییر رابطه به دشمنی
            cursor.execute('''
            UPDATE alliances 
            SET relation_type = 'WAR'
            WHERE (country1_id = ? AND country2_id = ?)
               OR (country1_id = ? AND country2_id = ?)
            ''', (country_id, traitor['id'], traitor['id'], country_id))
            
            cursor.execute('''
            INSERT INTO events (event_type, country_id, target_country_id, description)
            VALUES (?, ?, ?, ?)
            ''', ('BETRAYAL', country_id, traitor['id'], 
                  f"خیانت AI به {traitor['name']}"))
            
            self.db.conn.commit()
            return f"AI خیانت به {traitor['name']}"
        return None
    
    def process_all_ai_decisions(self):
        """پردازش تصمیم‌های تمام AIها"""
        ai_countries = self.db.get_ai_countries()
        all_decisions = []
        
        for country in ai_countries:
            decisions = self.ai_decision_maker(country['id'])
            all_decisions.extend(decisions)
        
        return all_decisions
    
    def calculate_battle_outcome(self, attacker_id, defender_id):
        """محاسبه نتیجه نبرد"""
        attacker_army = self.db.get_country_army(attacker_id)
        defender_army = self.db.get_country_army(defender_id)
        
        # محاسبه قدرت با درنظرگرفتن شانس
        attacker_power = attacker_army['power'] * random.uniform(0.8, 1.2)
        defender_power = defender_army['power'] * random.uniform(0.8, 1.2)
        
        if attacker_power > defender_power:
            # برنده حمله‌کننده
            damage_ratio = defender_power / attacker_power
            
            # تلفات
            attacker_loss = int(attacker_army['infantry'] * 0.2 * (1 - damage_ratio))
            defender_loss = int(defender_army['infantry'] * 0.4)
            
            # غنیمت
            loot_gold = random.randint(100, 300)
            loot_food = random.randint(200, 500)
            
            return {
                'winner': attacker_id,
                'attacker_loss': max(attacker_loss, 10),
                'defender_loss': max(defender_loss, 20),
                'loot': {'gold': loot_gold, 'food': loot_food}
            }
        else:
            # برنده مدافع
            defender_loss = int(defender_army['infantry'] * 0.15)
            attacker_loss = int(attacker_army['infantry'] * 0.3)
            
            return {
                'winner': defender_id,
                'attacker_loss': max(attacker_loss, 20),
                'defender_loss': max(defender_loss, 10),
                'loot': {'gold': 0, 'food': 0}
            }
