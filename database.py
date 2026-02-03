import sqlite3
import logging
from config import DB_NAME

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # جدول بازیکنان
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            country_id INTEGER,
            joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
        ''')
        
        # جدول کشورها
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS countries (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE,
            controller TEXT DEFAULT 'AI', -- 'HUMAN' یا 'AI'
            player_id INTEGER,
            specialty TEXT,
            color TEXT,
            is_active BOOLEAN DEFAULT 1
        )
        ''')
        
        # جدول منابع
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS resources (
            country_id INTEGER PRIMARY KEY,
            gold INTEGER DEFAULT 1000,
            iron INTEGER DEFAULT 500,
            stone INTEGER DEFAULT 800,
            food INTEGER DEFAULT 1200,
            last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # جدول ارتش
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS army (
            country_id INTEGER PRIMARY KEY,
            level INTEGER DEFAULT 1,
            infantry INTEGER DEFAULT 100,
            cavalry INTEGER DEFAULT 20,
            archers INTEGER DEFAULT 30,
            defense INTEGER DEFAULT 50,
            power INTEGER DEFAULT 150,
            last_training TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # جدول اتحادها
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS alliances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country1_id INTEGER,
            country2_id INTEGER,
            relation_type TEXT, -- 'ALLIANCE', 'WAR', 'NEUTRAL'
            strength INTEGER DEFAULT 50,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(country1_id, country2_id)
        )
        ''')
        
        # جدول فصل
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS seasons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            season_number INTEGER,
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            winner_country_id INTEGER,
            winner_player_id INTEGER,
            is_active BOOLEAN DEFAULT 0
        )
        ''')
        
        # جدول رویدادها
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT,
            country_id INTEGER,
            target_country_id INTEGER,
            description TEXT,
            resources_change TEXT, -- JSON
            army_change TEXT, -- JSON
            event_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        self.conn.commit()
        self.initialize_countries()
    
    def initialize_countries(self):
        """مقداردهی اولیه کشورها"""
        from config import ANCIENT_COUNTRIES
        
        cursor = self.conn.cursor()
        
        for country in ANCIENT_COUNTRIES:
            cursor.execute('''
            INSERT OR IGNORE INTO countries (id, name, specialty, color) 
            VALUES (?, ?, ?, ?)
            ''', (country['id'], country['name'], country['specialty'], country['color']))
        
        self.conn.commit()
    
    def get_country_by_id(self, country_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM countries WHERE id = ?', (country_id,))
        return cursor.fetchone()
    
    def get_player_country(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT c.* FROM players p
        JOIN countries c ON p.country_id = c.id
        WHERE p.user_id = ? AND p.is_active = 1
        ''', (user_id,))
        return cursor.fetchone()
    
    def assign_country_to_player(self, country_id, user_id, username, full_name):
        cursor = self.conn.cursor()
        
        # بررسی اینکه کشور قبلاً اختصاص داده نشده باشد
        cursor.execute('SELECT controller FROM countries WHERE id = ?', (country_id,))
        country = cursor.fetchone()
        
        if country and country['controller'] == 'AI':
            # ثبت بازیکن
            cursor.execute('''
            INSERT OR REPLACE INTO players (user_id, username, full_name, country_id, is_active)
            VALUES (?, ?, ?, ?, 1)
            ''', (user_id, username, full_name, country_id))
            
            # به‌روزرسانی کشور
            cursor.execute('''
            UPDATE countries 
            SET controller = 'HUMAN', player_id = ?
            WHERE id = ?
            ''', (user_id, country_id))
            
            # ایجاد منابع اولیه
            cursor.execute('''
            INSERT OR REPLACE INTO resources (country_id) 
            VALUES (?)
            ''', (country_id,))
            
            # ایجاد ارتش اولیه
            cursor.execute('''
            INSERT OR REPLACE INTO army (country_id) 
            VALUES (?)
            ''', (country_id,))
            
            self.conn.commit()
            return True
        
        return False
    
    def get_ai_countries(self):
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT * FROM countries 
        WHERE controller = 'AI' AND is_active = 1
        ORDER BY id
        ''')
        return cursor.fetchall()
    
    def get_active_season(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM seasons WHERE is_active = 1')
        return cursor.fetchone()
    
    def start_new_season(self, season_number):
        cursor = self.conn.cursor()
        cursor.execute('''
        UPDATE seasons SET is_active = 0
        ''')
        cursor.execute('''
        INSERT INTO seasons (season_number, start_date, is_active)
        VALUES (?, CURRENT_TIMESTAMP, 1)
        ''', (season_number,))
        self.conn.commit()
    
    def get_all_players(self):
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT p.*, c.name as country_name 
        FROM players p
        JOIN countries c ON p.country_id = c.id
        WHERE p.is_active = 1
        ''')
        return cursor.fetchall()
    
    def update_resources(self, country_id, resources_dict):
        cursor = self.conn.cursor()
        set_clause = ', '.join([f"{key} = {key} + ?" for key in resources_dict.keys()])
        values = list(resources_dict.values())
        values.append(country_id)
        
        query = f'''
        UPDATE resources 
        SET {set_clause}, last_update = CURRENT_TIMESTAMP
        WHERE country_id = ?
        '''
        cursor.execute(query, values)
        self.conn.commit()
    
    def get_country_resources(self, country_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM resources WHERE country_id = ?', (country_id,))
        return cursor.fetchone()
    
    def get_country_army(self, country_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM army WHERE country_id = ?', (country_id,))
        return cursor.fetchone()
    
    def upgrade_army_level(self, country_id, cost):
        """ارتقای سطح ارتش"""
        cursor = self.conn.cursor()
        
        # افزایش سطح و قدرت
        cursor.execute('''
        UPDATE army 
        SET level = level + 1, 
            power = power + 50,
            defense = defense + 20,
            last_training = CURRENT_TIMESTAMP
        WHERE country_id = ?
        ''', (country_id,))
        
        # کم کردن منابع
        cursor.execute('''
        UPDATE resources 
        SET gold = gold - ?,
            iron = iron - ?,
            food = food - ?,
            last_update = CURRENT_TIMESTAMP
        WHERE country_id = ?
        ''', (cost.get('gold', 0), cost.get('iron', 0), cost.get('food', 0), country_id))
        
        self.conn.commit()
    
    def close(self):
        self.conn.close()
