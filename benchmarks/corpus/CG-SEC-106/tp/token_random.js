// MUST trigger CG-SEC-106
function mint() {
  const sessionToken = Math.random().toString(36).slice(2);
  const csrf = "x" + Math.random();
  return { sessionToken, csrf };
}
