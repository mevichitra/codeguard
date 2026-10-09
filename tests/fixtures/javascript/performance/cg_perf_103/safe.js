const ids = users.reduce((acc, u) => {
  acc.push(u.id);
  return acc;
}, []);
const merged = items.reduce((acc, x) => [...x.tags], []);
