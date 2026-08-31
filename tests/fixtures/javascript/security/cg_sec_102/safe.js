// MUST NOT trigger CG-SEC-102
const cp = require("child_process");
function checkout(branch) {
  cp.execFile("git", ["checkout", branch]);
  cp.exec("git status");
}
