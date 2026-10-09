const https = require("https");
const fs = require("fs");

const agent = new https.Agent({ rejectUnauthorized: true, ca: fs.readFileSync("ca.pem") });
process.env.NODE_TLS_REJECT_UNAUTHORIZED = "1";
