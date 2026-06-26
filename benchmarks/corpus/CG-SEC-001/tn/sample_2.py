# CG-SEC-001 tn sample 2: named parameters (safe)
import sqlite3

def get_user(email):
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    # SAFE
    c.execute("SELECT * FROM users WHERE email = :email", {"email": email})
    return c.fetchone()
