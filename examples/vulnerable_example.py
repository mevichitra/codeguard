"""
examples/vulnerable_example.py — intentionally insecure code for demo purposes.

Run:  codeguard scan examples/vulnerable_example.py
"""

import pickle
import sqlite3
import subprocess

# CG-SEC-002: hardcoded secret
api_key = "sk-super-secret-12345"


def get_user(username: str) -> dict:
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    # CG-SEC-001: SQL injection via f-string
    cursor.execute(f"SELECT * FROM users WHERE username = '{username}'")
    return cursor.fetchone()


def run_report(report_name: str) -> str:
    # CG-SEC-005: shell=True with dynamic argument
    result = subprocess.run(
        f"generate_report.sh {report_name}", shell=True, capture_output=True, text=True
    )
    return result.stdout


def load_cached_model(data: bytes) -> object:
    # CG-SEC-004: unsafe deserialization
    return pickle.loads(data)


def evaluate(expression: str) -> object:
    # CG-SEC-003: eval on dynamic input
    return eval(expression)
