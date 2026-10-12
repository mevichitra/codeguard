# Request data flows through a variable into a SQL query.
import sqlite3

from flask import request


def search():
    term = request.args.get("q", "")
    clause = "name LIKE '%" + term + "%'"
    sql = "SELECT * FROM products WHERE " + clause
    db = sqlite3.connect("shop.db")
    return db.execute(sql).fetchall()


@app.route("/user/<user_id>")
def user(user_id):
    cur = db.cursor()
    cur.execute(f"SELECT * FROM users WHERE id = {user_id}")
