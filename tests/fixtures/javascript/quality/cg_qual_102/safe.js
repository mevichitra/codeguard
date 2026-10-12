try {
  risky();
} catch (err) {
  // optional feature: absence is fine
}
try {
  risky();
} catch (err) {
  console.error(err);
}
