"""
Database models and initialization for VPN/V2Ray service
"""
import sqlite3
import os
from datetime import datetime, timedelta
import uuid as uuid_module


class Database:
    def __init__(self, db_path='database.db'):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Initialize database with all required tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Plans table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                duration_days INTEGER NOT NULL,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # Subscriptions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plan_id INTEGER NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (plan_id) REFERENCES plans(id)
            )
        ''')
        
        # V2Ray configs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS v2ray_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                uuid TEXT,
                server TEXT,
                port INTEGER,
                protocol TEXT DEFAULT 'vmess',
                vless_url TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Add vless_url column if it doesn't exist (for existing databases)
        try:
            cursor.execute('ALTER TABLE v2ray_configs ADD COLUMN vless_url TEXT')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Payment submissions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payment_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plan_id INTEGER NOT NULL,
                bank_name TEXT NOT NULL,
                account_number TEXT NOT NULL,
                transaction_id TEXT,
                payment_slip_filename TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                submitted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TEXT,
                reviewed_by INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (plan_id) REFERENCES plans(id),
                FOREIGN KEY (reviewed_by) REFERENCES users(id)
            )
        ''')
        
        # Servers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                country TEXT NOT NULL,
                city TEXT NOT NULL,
                status TEXT DEFAULT 'online',
                location_code TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # Insert default servers if they don't exist
        cursor.execute('SELECT COUNT(*) FROM servers')
        if cursor.fetchone()[0] == 0:
            default_servers = [
                ('United States', 'United States', 'New York', 'online', 'US-NY'),
                ('United Kingdom', 'United Kingdom', 'London', 'online', 'UK-LON'),
                ('Germany', 'Germany', 'Frankfurt', 'online', 'DE-FRA'),
                ('Japan', 'Japan', 'Tokyo', 'online', 'JP-TYO'),
                ('Singapore', 'Singapore', 'Singapore', 'online', 'SG-SIN'),
                ('Canada', 'Canada', 'Toronto', 'online', 'CA-TOR'),
            ]
            cursor.executemany(
                'INSERT INTO servers (name, country, city, status, location_code) VALUES (?, ?, ?, ?, ?)',
                default_servers
            )
        
        # Create uploads directory for payment slips
        uploads_dir = 'uploads'
        if not os.path.exists(uploads_dir):
            os.makedirs(uploads_dir)
        
        # Insert default plans if they don't exist
        cursor.execute('SELECT COUNT(*) FROM plans')
        if cursor.fetchone()[0] == 0:
            default_plans = [
                ('7 Days Plan', 5.99, 7),
                ('30 Days Plan', 19.99, 30),
                ('90 Days Plan', 49.99, 90)
            ]
            cursor.executemany(
                'INSERT INTO plans (name, price, duration_days) VALUES (?, ?, ?)',
                default_plans
            )
        
        # Create default admin user (password: admin123)
        # Password hash for 'admin123' using bcrypt
        import bcrypt
        admin_hash = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute('SELECT COUNT(*) FROM users WHERE email = ?', ('admin@vpnservice.com',))
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                'INSERT INTO users (email, password_hash, is_active) VALUES (?, ?, ?)',
                ('admin@vpnservice.com', admin_hash, 1)
            )
        
        conn.commit()
        conn.close()
    
    def execute_query(self, query, params=()):
        """Execute a query and return results"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchall()
        conn.commit()
        conn.close()
        return result
    
    def execute_one(self, query, params=()):
        """Execute a query and return single result"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchone()
        conn.commit()
        conn.close()
        return result


# Database instance
db = Database()


