import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { extractLandmarks } from "../frontend/detection/preprocess.js";
import * as tf from "@tensorflow/tfjs";

// Load a tfjs layers model from local files (no native deps, no file:// handler needed)
async function loadLocalLayersModel(modelJsonPath) {
  const modelJSON = JSON.parse(fs.readFileSync(modelJsonPath, "utf8"));
  const dir = path.dirname(modelJsonPath);
  const specs = [];
  const buffers = [];
  for (const group of modelJSON.weightsManifest) {
    for (const p of group.paths) buffers.push(fs.readFileSync(path.join(dir, p)));
    specs.push(...group.weights);
  }
  const wd = Buffer.concat(buffers);
  const handler = {
    load: async () => ({
      modelTopology: modelJSON.modelTopology,
      weightSpecs: specs,
      weightData: wd.buffer.slice(wd.byteOffset, wd.byteOffset + wd.byteLength),
      format: modelJSON.format,
      generatedBy: modelJSON.generatedBy,
      convertedBy: modelJSON.convertedBy,
    }),
  };
  return tf.loadLayersModel(handler);
}

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

// --- Static model parity ---
const staticExpected = JSON.parse(fs.readFileSync(path.join(F, "static_expected.json"), "utf8"));
const staticModel = await loadLocalLayersModel(
  path.join(__dirname, "..", "frontend", "detection", "models", "static", "model.json")
);
const input = tf.tensor2d([Array.from(extractLandmarks(raw))]); // shape [1,63]
const out = staticModel.predict(input);
const probs = Array.from(await out.data());
const argmax = probs.indexOf(Math.max(...probs));
if (argmax !== staticExpected.argmax) {
  throw new Error(`static argmax ${argmax} != Python ${staticExpected.argmax}`);
}
assertClose(probs, staticExpected.probs, 1e-3, "static-model probs");
console.log(`PASS static-model argmax (${argmax})`);

console.log("ALL PARITY CHECKS PASSED");
