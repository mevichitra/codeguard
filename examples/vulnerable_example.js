/*
 * examples/vulnerable_example.js -- intentionally insecure code for demo purposes.
 *
 * Run:  codeguard scan examples/vulnerable_example.js
 */

const cp = require("child_process");

// CG-SEC-105: hardcoded secret
const apiKey = "sk-live-super-secret-12345";

function runReport(userInput, branch) {
  // CG-SEC-101: eval on user input
  const parsed = eval(userInput);

  // CG-SEC-102: shell command injection
  cp.execSync("git checkout " + branch);

  // CG-SEC-106: Math.random() for a security token
  const sessionToken = Math.random().toString(36).slice(2);

  return { parsed, sessionToken, apiKey };
}

function render(el, userHtml) {
  // CG-SEC-103: DOM XSS sink
  el.innerHTML = userHtml;
}

module.exports = { runReport, render };
