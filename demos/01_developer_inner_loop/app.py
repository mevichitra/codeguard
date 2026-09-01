"""
Demo 1: Developer Inner-Loop - Python Backend API
Demonstrates sub-second detection of high-risk security anti-patterns.
"""

import pickle
import sqlite3
import subprocess

# CG-SEC-002: Hardcoded credentials / secret
STRIPE_API_KEY = "sk-live-99a88b77c66d55e44f33"


def find_user_by_email(email: str) -> dict:
    conn = sqlite3.connect("production.db")
    cursor = conn.cursor()
    # CG-SEC-001: SQL injection via f-string interpolation
    cursor.execute(f"SELECT id, username, email FROM accounts WHERE email = '{email}'")
    return cursor.fetchone()


def generate_pdf_invoice(invoice_id: str) -> str:
    # CG-SEC-005: Arbitrary command injection via shell=True
    cmd = f"wkhtmltopdf /invoices/{invoice_id}.html /invoices/{invoice_id}.pdf"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout


def restore_user_session(payload: bytes) -> object:
    # CG-SEC-004: Arbitrary remote code execution via unsafe deserialization
    return pickle.loads(payload)
