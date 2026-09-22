import assert from "node:assert";
import { PredictionSmoother } from "../frontend/detection/smoother.js";

// stable_count identical high-confidence predictions -> accept once, then cooldown
const s = new PredictionSmoother({ windowSize: 8, stableCount: 4, cooldown: 8, confidenceThreshold: 0.65 });
let accepted = null;
for (let i = 0; i < 4; i++) { const [a] = s.update(5, 0.9); if (a !== null) accepted = a; }
assert.strictEqual(accepted, 5, "should accept class 5 after 4 stable frames");

// immediately after acceptance, cooldown blocks re-acceptance
const [a2] = s.update(5, 0.9);
assert.strictEqual(a2, null, "cooldown should block immediate re-accept");

// low confidence never accepts
const s2 = new PredictionSmoother({ windowSize: 8, stableCount: 4, cooldown: 8, confidenceThreshold: 0.65 });
let any = null;
for (let i = 0; i < 8; i++) { const [a] = s2.update(3, 0.5); if (a !== null) any = a; }
assert.strictEqual(any, null, "low confidence must not be accepted");

console.log("PASS smoother unit tests");
