def q(cur):
    cur.execute("SELECT " + " * " + " FROM users WHERE active = 1")
