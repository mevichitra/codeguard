# CG-SEC-001 tp sample 1: f-string in execute
import sqlite3

def login(username, password):
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    # VULNERABLE
    c.execute(f"SELECT * FROM users WHERE name='{username}' AND pass='{password}'")
    return c.fetchone()
