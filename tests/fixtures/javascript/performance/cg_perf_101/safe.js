async function loadAll(ids, stream) {
  const users = await Promise.all(ids.map(async (id) => await fetchUser(id)));
  for await (const chunk of stream) {
    await write(chunk);
  }
  return users;
}
