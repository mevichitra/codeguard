import sqlite3
import hashlib

def authenticate_user(username, password):
    """Vulnerable login function with SQL injection"""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # VULNERABILITY: SQL Injection - user input directly concatenated
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    cursor.execute(query)
    result = cursor.fetchone()
    
    conn.close()
    return result is not None

def weak_password_hash(password):
    """VULNERABILITY: Weak cryptographic function"""
    return hashlib.md5(password.encode()).hexdigest()

class UserSession:
    def __init__(self):
        # VULNERABILITY: Hardcoded credentials
        self.admin_key = "admin123"
        self.secret_token = "hardcoded_secret_2024"
        
    def validate_admin(self, provided_key):
        return provided_key == self.admin_key

# VULNERABILITY: Sensitive data in logs
def log_user_activity(username, password, action):
    with open('activity.log', 'a') as f:
        f.write(f"User: {username}, Password: {password}, Action: {action}\n")