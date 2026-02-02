import sqlite3
import json
from datetime import datetime
from config import COUNTRIES, ARMY_LEVELS

class Database:
    def __init__(self, db_name='ancient_war.db'):
        self.db_name = db_name
        self.init_database()
    
    def get_connection(self):
        return sqlite3.connect(self.db_name)
    
    def init_database(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # جدول بازیکنان
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                country_code TEXT,
                controller_type TEXT DEFAULT 'HUMAN',
                is_active INTEGER DEFAULT 1,
                join_date TEXT,
                FOREIGN KEY (country_code) REFERENCES countries(code)
            )
        ''')
        
        # جدول کشورها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS countries (
                code TEXT PRIMARY KEY,
                name TEXT,
                controller_type TEXT DEFAULT 'AI',
                player_id INTEGER,
                army_level INTEGER DEFAULT 1,
                gold INTEGER DEFAULT 1000,
                iron INTEGER DEFAULT 500,
                stone INTEGER DEFAULT 500,
                food INTEGER DEFAULT 1000,
                power_score INTEGER DEFAULT 0,
                last_update TEXT,
                FOREIGN KEY (player_id) REFERENCES players(user_id)
            )
        ''')
        
        # جدول ارتش
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS army (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                country_code TEXT,
                soldiers_count INTEGER DEFAULT 100,
                cavalry_count INTEGER DEFAULT 20,
                siege_count INTEGER DEFAULT 5,
                level INTEGER DEFAULT 1,
                total_power INTEGER DEFAULT 0,
                FOREIGN KEY (country_code) REFERENCES countries(code)
            )
        ''')
        
        # جدول اتحادها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alliances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                country1_code TEXT,
                country2_code TEXT,
                relationship_score INTEGER DEFAULT 50,
                is_active INTEGER DEFAULT 1,
                created_date TEXT,
                FOREIGN KEY (country1_code) REFERENCES countries(code),
                FOREIGN KEY (country2_code) REFERENCES countries(code)
            )
        ''')
        
        # جدول رویدادها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                description TEXT,
                countries_involved TEXT,  # JSON array
                date_time TEXT,
                season_id INTEGER
            )
        ''')
        
        # جدول فصل‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS seasons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_date TEXT,
                end_date TEXT,
                is_active INTEGER DEFAULT 0,
                winner_country TEXT,
                winner_player_id INTEGER
            )
        ''')
        
        # جدول پیام‌های وزیر
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS advisor_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                country_code TEXT,
                message_type TEXT,
                message TEXT,
                is_read INTEGER DEFAULT 0,
                created_date TEXT
            )
        ''')
        
        # ایجاد کشورها اگر وجود ندارند
        for code, info in COUNTRIES.items():
            cursor.execute('''
                INSERT OR IGNORE INTO countries (code, name, controller_type, last_update)
                VALUES (?, ?, 'AI', ?)
            ''', (code, info['name'], datetime.now().isoformat()))
            
            # ایجاد ارتش اولیه برای کشور
            cursor.execute('''
                INSERT OR IGNORE INTO army (country_code, soldiers_count, cavalry_count, siege_count, level, total_power)
                VALUES (?, 100, 20, 5, 1, 125)
            ''', (code,))
        
        conn.commit()
        conn.close()
    
    def add_player(self, user_id, username, country_code):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # بررسی وجود بازیکن
        cursor.execute('SELECT * FROM players WHERE user_id = ?', (user_id,))
        if cursor.fetchone():
            conn.close()
            return False
        
        # اضافه کردن بازیکن
        cursor.execute('''
            INSERT INTO players (user_id, username, country_code, controller_type, join_date)
            VALUES (?, ?, ?, 'HUMAN', ?)
        ''', (user_id, username, country_code, datetime.now().isoformat()))
        
        # به‌روزرسانی کشور
        cursor.execute('''
            UPDATE countries 
            SET controller_type = 'HUMAN', player_id = ?, last_update = ?
            WHERE code = ?
        ''', (user_id, datetime.now().isoformat(), country_code))
        
        conn.commit()
        conn.close()
        return True
    
    def get_ai_countries(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT code, name FROM countries 
            WHERE controller_type = 'AI' 
            ORDER BY name
        ''')
        
        countries = cursor.fetchall()
        conn.close()
        return countries
    
    def get_country_info(self, country_code):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.*, p.username, a.* 
            FROM countries c
            LEFT JOIN players p ON c.player_id = p.user_id
            LEFT JOIN army a ON c.code = a.country_code
            WHERE c.code = ?
        ''', (country_code,))
        
        result = cursor.fetchone()
        columns = [desc[0] for desc in cursor.description]
        
        if result:
            country_info = dict(zip(columns, result))
            conn.close()
            return country_info
        
        conn.close()
        return None
    
    def update_resources(self, country_code, gold_change=0, iron_change=0, stone_change=0, food_change=0):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE countries 
            SET gold = gold + ?, 
                iron = iron + ?, 
                stone = stone + ?, 
                food = food + ?,
                last_update = ?
            WHERE code = ?
        ''', (gold_change, iron_change, stone_change, food_change, datetime.now().isoformat(), country_code))
        
        conn.commit()
        conn.close()
        return True
    
    def upgrade_army(self, country_code):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # دریافت اطلاعات فعلی
        cursor.execute('SELECT army_level, gold FROM countries WHERE code = ?', (country_code,))
        country = cursor.fetchone()
        
        if not country:
            conn.close()
            return False, "کشور یافت نشد"
        
        current_level, gold = country
        next_level = current_level + 1
        
        if next_level > 5:
            conn.close()
            return False, "حداکثر سطح رسیده است"
        
        upgrade_cost = ARMY_LEVELS[next_level]['upgrade_cost']
        
        if gold < upgrade_cost:
            conn.close()
            return False, "طلا کافی نیست"
        
        # پرداخت هزینه
        cursor.execute('UPDATE countries SET gold = gold - ? WHERE code = ?', (upgrade_cost, country_code))
        
        # ارتقای ارتش
        cursor.execute('UPDATE countries SET army_level = ? WHERE code = ?', (next_level, country_code))
        cursor.execute('UPDATE army SET level = ? WHERE country_code = ?', (next_level, country_code))
        
        # محاسبه قدرت جدید
        new_power = ARMY_LEVELS[next_level]['power'] * 100
        cursor.execute('UPDATE army SET total_power = ? WHERE country_code = ?', (new_power, country_code))
        
        conn.commit()
        conn.close()
        return True, f"ارتش به سطح {next_level} ارتقا یافت!"
    
    def create_alliance(self, country1, country2):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # بررسی وجود اتحاد
        cursor.execute('''
            SELECT * FROM alliances 
            WHERE ((country1_code = ? AND country2_code = ?) 
            OR (country1_code = ? AND country2_code = ?)) 
            AND is_active = 1
        ''', (country1, country2, country2, country1))
        
        if cursor.fetchone():
            conn.close()
            return False, "اتحاد از قبل وجود دارد"
        
        # ایجاد اتحاد جدید
        cursor.execute('''
            INSERT INTO alliances (country1_code, country2_code, created_date)
            VALUES (?, ?, ?)
        ''', (country1, country2, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        return True, "اتحاد با موفقیت ایجاد شد"
    
    def start_season(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO seasons (start_date, is_active)
            VALUES (?, 1)
        ''', (datetime.now().isoformat(),))
        
        season_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return season_id
    
    def end_season(self, winner_country_code, winner_player_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE seasons 
            SET end_date = ?, is_active = 0, winner_country = ?, winner_player_id = ?
            WHERE is_active = 1
        ''', (datetime.now().isoformat(), winner_country_code, winner_player_id))
        
        conn.commit()
        conn.close()
        return True
    
    def get_active_season(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM seasons WHERE is_active = 1')
        season = cursor.fetchone()
        
        conn.close()
        return season
    
    def add_event(self, event_type, description, countries_involved):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        season = self.get_active_season()
        season_id = season[0] if season else None
        
        cursor.execute('''
            INSERT INTO events (event_type, description, countries_involved, date_time, season_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (event_type, description, json.dumps(countries_involved), datetime.now().isoformat(), season_id))
        
        conn.commit()
        conn.close()
        return True
