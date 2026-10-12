const ids = users.reduce((acc, u) => [...acc, u.id], []);
const byId = users.reduce((acc, u) => ({ ...acc, [u.id]: u }), {});
