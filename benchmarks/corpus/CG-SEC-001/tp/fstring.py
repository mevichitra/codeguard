import sqlite3
def q(db, uid):
    db.execute(f"SELECT * FROM users WHERE id = {uid}")
