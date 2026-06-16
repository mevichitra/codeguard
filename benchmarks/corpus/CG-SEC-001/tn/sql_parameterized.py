def get_user(uid):
    cursor.execute("SELECT * FROM users WHERE id = %s", (uid,))
