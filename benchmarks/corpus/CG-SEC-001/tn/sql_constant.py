def get_all():
    table = "users"
    cursor.execute("SELECT * FROM " + table)
