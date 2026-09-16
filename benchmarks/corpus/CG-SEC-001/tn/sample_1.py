# CG-SEC-001 tn sample 1: parameterized query (safe)
import sqlite3

def login(username, password):
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    # SAFE
    c.execute("SELECT * FROM users WHERE name=? AND pass=?", (username, password))
    return c.fetchone()
