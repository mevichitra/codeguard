def get_user(name):
    query = "SELECT * FROM users WHERE name = '{}'".format(name)
    cursor.execute(query)
