/**
 * build_frontend.js — Local Frontend Build and Verification Pipeline
 */

const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

console.log("=== BTCognitive Frontend Build & Smoke Verification ===");

// 1. Verify module syntax
const filesToCheck = [
  "web/app.js",
  "web_src/api_client.js",
  "web_src/websocket.js",
  "web_src/formatters.js",
  "tests_frontend.js"
];

for (const f of filesToCheck) {
  process.stdout.write(`Checking ${f}... `);
  try {
    execSync(`node --check ${f}`, { stdio: "pipe" });
    console.log("OK");
  } catch (err) {
    console.error(`FAILED: ${err.message}`);
    process.exit(1);
  }
}

// 2. Verify static assets exist
const requiredAssets = [
  "web/index.html",
  "web/styles.css",
  "web/app.js"
];

for (const a of requiredAssets) {
  process.stdout.write(`Verifying asset ${a}... `);
  if (!fs.existsSync(path.resolve(__dirname, a))) {
    console.error("MISSING!");
    process.exit(1);
  }
  const stat = fs.statSync(path.resolve(__dirname, a));
  console.log(`OK (${(stat.size / 1024).toFixed(1)} KB)`);
}

// 3. Run frontend unit test suite
console.log("\nRunning frontend unit tests...");
try {
  execSync("node tests_frontend.js", { stdio: "inherit" });
} catch {
  console.error("Frontend tests failed!");
  process.exit(1);
}

console.log("\n=== Frontend Build and Verification Complete: SUCCESS ===");
