@router.get("/items")
async def items(q: str, conn=Depends(get_conn)):
    rows = await conn.execute("SELECT * FROM items WHERE tag = '%s'" % q)
    return rows
