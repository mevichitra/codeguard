// MUST NOT trigger CG-SEC-106
function jitter() {
  const delay = Math.random() * 1000;
  const offset = Math.random();
  return delay + offset;
}
