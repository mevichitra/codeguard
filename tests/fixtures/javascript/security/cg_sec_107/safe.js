const crypto = require("crypto");

const etag = crypto.createHash("md5").update(body).digest("hex");
function hashPassword(password, salt) {
  return crypto.scryptSync(password, salt, 64).toString("hex");
}
const token = crypto.createHash("sha256").update(seed).digest("hex");
