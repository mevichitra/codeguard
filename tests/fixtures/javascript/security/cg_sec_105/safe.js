// MUST NOT trigger CG-SEC-105
const password = process.env.PASSWORD;
const config = { apiKey: readSecret("apiKey") };
const label = "password";
