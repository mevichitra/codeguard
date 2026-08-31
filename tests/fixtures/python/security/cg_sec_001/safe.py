# Fixture: CG-SEC-001 safe
# This file MUST NOT trigger CG-SEC-001.
# Shows correct parameterized query usage.

import sqlite3


def get_user_by_name(username: str) -> dict:
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    # SAFE: parameterized query with ? placeholder
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    return cursor.fetchone()


def get_user_by_id(user_id: int) -> dict:
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    # SAFE: parameterized query with %s placeholder (DB-API style)
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    return cursor.fetchone()


def search_products(term: str) -> list:
    conn = sqlite3.connect("shop.db")
    cursor = conn.cursor()
    # SAFE: parameterized LIKE query
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", (f"%{term}%",))
    return cursor.fetchall()


def get_all_users() -> list:
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    # SAFE: fully literal query, no user input
    cursor.execute("SELECT * FROM users WHERE active = 1")
    return cursor.fetchall()
