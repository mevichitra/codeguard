def delete(cur, table):
    cur.execute("DELETE FROM " + table + " WHERE 1=1")
