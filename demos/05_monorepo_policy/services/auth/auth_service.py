"""Auth Service: Mission critical component."""
import sqlite3

def authenticate(username: str):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    # CG-SEC-001: Will be reported as CRITICAL due to severity remapping in codeguard.toml
    cursor.execute(f"SELECT * FROM users WHERE username = '{username}'")
    return cursor.fetchone()
