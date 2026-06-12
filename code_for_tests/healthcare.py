import getpass
import json
import os
import sqlite3
from datetime import datetime

# -----------------------------
# INSECURE CONFIG (ON PURPOSE)
# -----------------------------

# VULNERABILITY 1: Hard-coded "secrets" in source code
DB_NAME = "clinic.db"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"  # VULNERABLE: Plain-text hardcoded password

# VULNERABILITY 2: Logging sensitive data (PHI + credentials) to a world-readable file
LOG_FILE = "clinic_log.txt"


def log(message):
    """VULNERABLE: Logs sensitive info in plain text to a file."""
    with open(LOG_FILE, "a") as f:
        f.write(f"[{datetime.now()}] {message}\n")


def init_db():
    """Create a simple patients table if it doesn't exist."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            age INTEGER,
            diagnosis TEXT,
            ssn TEXT  -- pretend social security / ID
        )
        """
    )
    conn.commit()
    conn.close()


def seed_data():
    """Insert some dummy patients (for demo)."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO patients (name, age, diagnosis, ssn) VALUES ('Alice', 34, 'Flu', '123-45-6789')"
    )
    c.execute(
        "INSERT INTO patients (name, age, diagnosis, ssn) VALUES ('Bob', 52, 'Diabetes', '987-65-4321')"
    )
    conn.commit()
    conn.close()


def insecure_login():
    """
    VULNERABILITY 3: Insecure authentication.
    - Hard-coded username/password
    - Logs credentials in plain text
    """
    print("=== Clinic Admin Login ===")
    username = input("Username: ")
    password = getpass.getpass("Password: ")

    # VULNERABLE: Logging credentials
    log(f"LOGIN ATTEMPT user={username}, password={password}")

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        print("Login successful (insecure)!")
        return True
    else:
        print("Invalid credentials")
        return False


def search_patient_insecure():
    """
    VULNERABILITY 4: SQL Injection via string concatenation.
    - Directly embeds user input into SQL query.
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    print("\n=== Search Patient (INSECURE) ===")
    # VULNERABLE: No validation, direct use in SQL
    name_filter = input("Enter patient name (or partial): ")

    # VULNERABLE: SQL injection possible here
    query = f"SELECT id, name, age, diagnosis, ssn FROM patients WHERE name LIKE '%{name_filter}%'"
    print(f"[DEBUG] Executing query: {query}")
    log(f"Running insecure patient search with filter={name_filter}")

    try:
        for row in c.execute(query):
            print(
                f"ID={row[0]}, Name={row[1]}, Age={row[2]}, Dx={row[3]}, SSN={row[4]}"
            )
    except Exception as e:
        print("Error searching patients:", e)
        log(f"Error in insecure search: {e}")
    finally:
        conn.close()


def export_patients_insecure():
    """
    VULNERABILITY 5: Insecure file export path and permissions.
    - Lets user specify arbitrary path (path traversal, overwrite risk).
    - Exports sensitive data (including SSNs) in plain JSON.
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    print("\n=== Export Patients (INSECURE) ===")
    # VULNERABLE: arbitrary path, could be '../../etc/passwd' etc.
    export_path = input("Enter path to export patient data (e.g., patients.json): ")

    log(f"Exporting patient data to {export_path}")

    c.execute("SELECT id, name, age, diagnosis, ssn FROM patients")
    patients = [
        {
            "id": row[0],
            "name": row[1],
            "age": row[2],
            "diagnosis": row[3],
            "ssn": row[4],  # VULNERABLE: sensitive ID leaked
        }
        for row in c.fetchall()
    ]
    conn.close()

    # VULNERABLE: no checks, world-readable file, sensitive info in plain JSON
    with open(export_path, "w") as f:
        json.dump(patients, f, indent=2)

    print(f"Exported {len(patients)} patients to {export_path}")
    log(f"Export complete for {len(patients)} patients")


def debug_menu_insecure():
    """
    VULNERABILITY 6: Dangerous use of eval on user input.
    - Allows arbitrary code execution.
    """
    print("\n=== Debug Menu (INSECURE) ===")
    print("You can run a Python expression here for 'debugging'.")
    expr = input("Enter Python code to eval: ")

    log(f"DEBUG EVAL requested: {expr}")
    # VULNERABLE: arbitrary code execution
    try:
        result = eval(expr)
        print("Result:", result)
    except Exception as e:
        print("Error in eval:", e)
        log(f"Eval error: {e}")


def main():
    # Initialize DB and seed data if first run
    if not os.path.exists(DB_NAME):
        init_db()
        seed_data()

    if not insecure_login():
        return

    while True:
        print(
            """
=== Clinic Admin Panel (INSECURE DEMO) ===
1. Search patient (insecure SQL)
2. Export all patients (insecure file export)
3. Debug menu (eval)
4. Exit
"""
        )
        choice = input("Choose an option: ")

        if choice == "1":
            search_patient_insecure()
        elif choice == "2":
            export_patients_insecure()
        elif choice == "3":
            debug_menu_insecure()
        elif choice == "4":
            print("Goodbye.")
            break
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
