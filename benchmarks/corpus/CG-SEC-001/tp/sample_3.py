# CG-SEC-001 tp sample 3: % formatting in execute
import sqlite3

def search(query):
    conn = sqlite3.connect('search.db')
    c = conn.cursor()
    # VULNERABLE
    c.execute("SELECT * FROM docs WHERE content LIKE '%' || '%s' || '%'" % query)
    return c.fetchall()
