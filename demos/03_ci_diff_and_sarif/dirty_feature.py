"""
Demo 3: Pull Request Feature Branch
Demonstrates diff-aware CI scanning and SARIF / GitHub Actions integration.
"""

import sqlite3


def search_products(query_term: str):
    conn = sqlite3.connect("catalog.db")
    cursor = conn.cursor()
    # CG-SEC-001: SQL injection introduced in PR branch
    cursor.execute(f"SELECT * FROM products WHERE name LIKE '%{query_term}%'")
    return cursor.fetchall()
