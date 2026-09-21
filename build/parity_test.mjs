import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { extractLandmarks } from "../frontend/detection/preprocess.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const F = path.join(__dirname, "fixtures");
const TOL = 1e-5;

function assertClose(a, b, tol, label) {
  if (a.length !== b.length) throw new Error(`${label}: length ${a.length} != ${b.length}`);
  let maxErr = 0;
  for (let i = 0; i < a.length; i++) maxErr = Math.max(maxErr, Math.abs(a[i] - b[i]));
  if (maxErr > tol) throw new Error(`${label}: max abs err ${maxErr} > ${tol}`);
  console.log(`PASS ${label} (max abs err ${maxErr.toExponential(2)})`);
}

// --- Preprocess parity ---
const raw = JSON.parse(fs.readFileSync(path.join(F, "landmarks_raw.json"), "utf8"));
const expected = JSON.parse(fs.readFileSync(path.join(F, "preprocess_expected.json"), "utf8"));
const got = Array.from(extractLandmarks(raw));
assertClose(got, expected, TOL, "preprocess");

console.log("ALL PARITY CHECKS PASSED");
