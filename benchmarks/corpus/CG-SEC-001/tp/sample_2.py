# CG-SEC-001 tp sample 2: .format() in execute
import sqlite3

def lookup_user(user_id):
    conn = sqlite3.connect('db.sqlite')
    c = conn.cursor()
    # VULNERABLE
    c.execute("SELECT * FROM users WHERE id = {}".format(user_id))
    return c.fetchall()
