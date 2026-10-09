const https = require("https");

const agent = new https.Agent({ rejectUnauthorized: false });
request({ url, strictSSL: false });
process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";
