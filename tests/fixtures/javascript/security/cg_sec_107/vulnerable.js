const crypto = require("crypto");

function hashPassword(password) {
  return crypto.createHash("md5").update(password).digest("hex");
}

const apiSignature = crypto.createHash("sha1").update(body).digest("hex");
