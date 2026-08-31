# Fixture: CG-SEC-001 vulnerable
# This file MUST trigger CG-SEC-001 (SQL via string formatting).
# Do not import or run this file — it contains intentionally insecure code.

import sqlite3


def get_user_by_name(username: str) -> dict:
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    # VULNERABLE: f-string in execute() — SQL injection
    cursor.execute(f"SELECT * FROM users WHERE username = '{username}'")
    return cursor.fetchone()


def get_user_by_id(user_id: int) -> dict:
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    # VULNERABLE: %-formatting in execute()
    cursor.execute("SELECT * FROM users WHERE id = %s" % user_id)
    return cursor.fetchone()


def search_products(term: str) -> list:
    conn = sqlite3.connect("shop.db")
    cursor = conn.cursor()
    # VULNERABLE: .format() in execute()
    cursor.execute("SELECT * FROM products WHERE name LIKE '{}'".format(term))
    return cursor.fetchall()


def delete_record(table: str, record_id: int) -> None:
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    # VULNERABLE: string concatenation in execute()
    cursor.execute("DELETE FROM " + table + " WHERE id = " + str(record_id))
