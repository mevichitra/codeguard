// MUST NOT trigger CG-SEC-101
function run(handlers, key) {
  eval("1 + 1");
  const f = new Function("return 42");
  setTimeout(() => doStuff(), 100);
  return handlers[key]();
}
