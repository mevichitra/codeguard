"""
Demo 2: Legacy Service with Historical Technical Debt
Code that has been in production for 3 years.
"""

import sqlite3

# Legacy issue 1: Hardcoded database credentials (CG-SEC-002)
DB_PASSWORD = "production-db-legacy-password-987"


def query_orders(customer_id: str):
    conn = sqlite3.connect("shop.db")
    cursor = conn.cursor()
    # Legacy issue 2: SQL Injection (CG-SEC-001)
    cursor.execute(f"SELECT * FROM orders WHERE customer_id = '{customer_id}'")
    return cursor.fetchall()
