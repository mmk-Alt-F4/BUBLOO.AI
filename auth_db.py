import sqlite3
import hashlib
import os

DB_FILE = "users.db"

def init_db():
    """Initialize the database with the users table."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash BLOB NOT NULL,
            salt BLOB NOT NULL,
            full_name TEXT
        )
    ''')
    conn.commit()
    conn.close()

def hash_password(password, salt=None):
    """Hash a password with a salt using PBKDF2."""
    if salt is None:
        salt = os.urandom(32)  # 32 bytes of salt
    
    # 100,000 iterations of SHA-256
    pwd_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000
    )
    return pwd_hash, salt

def register_user(username, password, full_name):
    """Register a new user."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Check if user already exists
    c.execute('SELECT username FROM users WHERE username = ?', (username,))
    if c.fetchone():
        conn.close()
        return False, "Username already exists."
    
    pwd_hash, salt = hash_password(password)
    
    try:
        c.execute('INSERT INTO users (username, password_hash, salt, full_name) VALUES (?, ?, ?, ?)',
                  (username, pwd_hash, salt, full_name))
        conn.commit()
        conn.close()
        return True, "User registered successfully."
    except Exception as e:
        conn.close()
        return False, f"Error registering user: {str(e)}"

def verify_user(username, password):
    """Verify a user's credentials."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute('SELECT password_hash, salt, full_name FROM users WHERE username = ?', (username,))
    row = c.fetchone()
    conn.close()
    
    if row:
        stored_hash, salt, full_name = row
        pwd_hash, _ = hash_password(password, salt)
        
        if pwd_hash == stored_hash:
            return {
                'username': username,
                'name': full_name,
                'email': username  # Treating username as email for consistency with Google Auth
            }
            
    return None
