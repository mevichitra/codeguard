// MUST trigger CG-SEC-101
function run(userInput, code) {
  eval(userInput);
  const f = new Function("return " + code);
  setTimeout("doStuff()", 100);
  return f;
}
