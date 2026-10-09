# Parameterized queries, sanitized input, and constants do not trigger.
from flask import request


def search(db):
    term = request.args.get("q", "")
    return db.execute("SELECT * FROM products WHERE name LIKE ?", (f"%{term}%",))


def by_id(db):
    uid = int(request.args["id"])
    return db.execute(f"SELECT * FROM users WHERE id = {uid}")


def helper(db, table):
    db.execute("SELECT * FROM " + "users")
