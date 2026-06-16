def get_user(uid):
    query = "SELECT * FROM users WHERE id = %s" % uid
    cursor.execute(query)
