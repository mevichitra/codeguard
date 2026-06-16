def get_user(uid):
    query = f"SELECT * FROM users WHERE id = {uid}"
    cursor.execute(query)
