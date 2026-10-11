import { readFileSync } from "node:fs";
import { verifyPackage } from "./verify.mjs";

const path = process.argv[2];
if (!path) { console.error("usage: node cli.mjs package.json"); process.exit(2); }
let pkg;
try { pkg = JSON.parse(readFileSync(path, "utf8")); } catch (e) { console.error(`cannot read package: ${e.message}`); process.exit(2); }
const { ok, checks } = await verifyPackage(pkg);
for (const c of checks) console.log(`${c.ok ? "PASS" : "FAIL"}  ${c.name}${!c.ok && c.detail ? `  (${c.detail})` : ""}`);
console.log(`\nRESULT: ${ok ? "PASS" : "FAIL"}`);
process.exit(ok ? 0 : 1);
