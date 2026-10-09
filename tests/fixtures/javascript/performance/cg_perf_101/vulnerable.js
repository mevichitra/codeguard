async function loadAll(ids) {
  const users = [];
  for (const id of ids) {
    users.push(await fetchUser(id));
  }
  let i = 0;
  while (i < ids.length) {
    await save(ids[i++]);
  }
  return users;
}
