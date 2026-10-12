# CG-SEC-001 tn sample 3: execute many with params (safe)
import sqlite3

def insert_users(users):
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    # SAFE
    c.executemany("INSERT INTO users (name) VALUES (?)", [(u,) for u in users])
    conn.commit()
