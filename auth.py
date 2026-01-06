"""
Authentication utilities for user registration and login
"""
import bcrypt
from models import db


def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password, password_hash):
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def register_user(email, password):
    """Register a new user"""
    # Check if user already exists
    existing = db.execute_one('SELECT id FROM users WHERE email = ?', (email,))
    if existing:
        return False, "Email already registered"
    
    # Validate email format (basic)
    if '@' not in email or '.' not in email:
        return False, "Invalid email format"
    
    # Validate password length
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    
    # Hash password and insert user
    password_hash = hash_password(password)
    try:
        db.execute_query(
            'INSERT INTO users (email, password_hash, is_active) VALUES (?, ?, ?)',
            (email, password_hash, 1)
        )
        return True, "Registration successful"
    except Exception as e:
        return False, f"Registration failed: {str(e)}"


def authenticate_user(email, password):
    """Authenticate a user and return user data if successful"""
    user = db.execute_one(
        'SELECT id, email, password_hash, is_active FROM users WHERE email = ?',
        (email,)
    )
    
    if not user:
        return None, "Invalid email or password"
    
    if not user['is_active']:
        return None, "Account is disabled"
    
    if not verify_password(password, user['password_hash']):
        return None, "Invalid email or password"
    
    return dict(user), None


def is_admin(email):
    """Check if user is admin"""
    return email == 'admin@vpnservice.com'

