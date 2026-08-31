// MUST trigger CG-SEC-102
const cp = require("child_process");
function checkout(branch, cmd) {
  cp.exec("git checkout " + branch);
  cp.execSync(cmd);
}
