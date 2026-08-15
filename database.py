import sqlite3
import time
from datetime import datetime

class Database:
    def __init__(self, db_file='bot.db'):
        self.conn = sqlite3.connect(db_file, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        # Users table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                first_seen INTEGER,
                last_active INTEGER,
                banned INTEGER DEFAULT 0,
                total_conversions INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0
            )
        ''')
        
        # Config table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # Logs table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER,
                level TEXT,
                message TEXT
            )
        ''')
        
        # Conversions table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                from_currency TEXT,
                timestamp INTEGER
            )
        ''')
        
        # Initialize default config
        self.cursor.execute('''
            INSERT OR IGNORE INTO config (key, value) VALUES 
            ('star_rate', '1.3'),
            ('footer', '━━━━━━━━━━━━━━━━━━\nMade by @cyber_amit'),
            ('admins', '[8603893462]')
        ''')
        
        self.conn.commit()
    
    def add_user(self, user_id, username, first_name, last_name=None):
        timestamp = int(time.time())
        self.cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, first_seen, last_active)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name, timestamp, timestamp))
        
        self.cursor.execute('''
            UPDATE users SET last_active = ?, username = ?, first_name = ?, last_name = ?
            WHERE user_id = ?
        ''', (timestamp, username, first_name, last_name, user_id))
        self.conn.commit()
    
    def get_user(self, user_id):
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone()
    
    def get_all_users(self):
        self.cursor.execute('SELECT user_id FROM users WHERE banned = 0')
        return self.cursor.fetchall()
    
    def get_user_count(self):
        self.cursor.execute('SELECT COUNT(*) FROM users')
        return self.cursor.fetchone()[0]
    
    def get_active_users(self, hours=24):
        timestamp = int(time.time()) - (hours * 3600)
        self.cursor.execute('SELECT COUNT(*) FROM users WHERE last_active > ?', (timestamp,))
        return self.cursor.fetchone()[0]
    
    def ban_user(self, user_id):
        self.cursor.execute('UPDATE users SET banned = 1 WHERE user_id = ?', (user_id,))
        self.conn.commit()
    
    def unban_user(self, user_id):
        self.cursor.execute('UPDATE users SET banned = 0 WHERE user_id = ?', (user_id,))
        self.conn.commit()
    
    def add_conversion(self, user_id, amount, currency):
        timestamp = int(time.time())
        self.cursor.execute('''
            INSERT INTO conversions (user_id, amount, from_currency, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (user_id, amount, currency, timestamp))
        self.cursor.execute('''
            UPDATE users SET total_conversions = total_conversions + 1
            WHERE user_id = ?
        ''', (user_id,))
        self.conn.commit()
    
    def get_config(self, key):
        self.cursor.execute('SELECT value FROM config WHERE key = ?', (key,))
        result = self.cursor.fetchone()
        return result[0] if result else None
    
    def set_config(self, key, value):
        self.cursor.execute('INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)', (key, value))
        self.conn.commit()
    
    def add_log(self, level, message):
        timestamp = int(time.time())
        self.cursor.execute('''
            INSERT INTO logs (timestamp, level, message) VALUES (?, ?, ?)
        ''', (timestamp, level, message))
        self.conn.commit()
    
    def get_logs(self, limit=50):
        self.cursor.execute('''
            SELECT timestamp, level, message FROM logs 
            ORDER BY timestamp DESC LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
    
    def close(self):
        self.conn.close()
