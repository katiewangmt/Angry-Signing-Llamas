// Assemble a flat static dist/ from frontend/ and zip it with index.html at the
// ROOT (ghg.gg requirement). Guards: index.html must be at the dist root, and
// the bundle must contain no secrets. Ships only static assets — no backend,
// no build scripts, no .env.
import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const root = path.dirname(fileURLToPath(import.meta.url)) + "/..";
const src = path.join(root, "frontend");
const dist = path.join(root, "dist");
const zip = path.join(root, "angry-signing-llamas-ghg.zip");

// Never ship: dev docs, OS junk. (Keep audio/music/README.txt — CC0 attribution.)
const EXCLUDE = new Set(["README.md", ".DS_Store", "spike.html"]);

fs.rmSync(dist, { recursive: true, force: true });
fs.mkdirSync(dist, { recursive: true });

function copyDir(from, to) {
  for (const entry of fs.readdirSync(from, { withFileTypes: true })) {
    if (EXCLUDE.has(entry.name)) continue;
    const s = path.join(from, entry.name);
    const d = path.join(to, entry.name);
    if (entry.isDirectory()) {
      fs.mkdirSync(d, { recursive: true });
      copyDir(s, d);
    } else {
      fs.copyFileSync(s, d);
    }
  }
}
copyDir(src, dist);

// Guard 1: index.html must be at the dist root.
if (!fs.existsSync(path.join(dist, "index.html"))) {
  throw new Error("index.html missing at dist root");
}

// Guard 2: no secrets anywhere in the bundle.
const leaked = execSync(
  `grep -rIlE "xi-api-key|ELEVENLABS_API_KEY|GEMINI_API_KEY|sk_[a-z0-9]{16}|AIza[0-9A-Za-z_-]{16}" ${JSON.stringify(dist)} || true`
).toString().trim();
if (leaked) throw new Error("Potential secret in dist:\n" + leaked);

// Guard 3: no off-origin runtime references in shipped HTML/JS/CSS.
const offOrigin = execSync(
  `grep -rInE "https?://(fonts\\.googleapis|fonts\\.gstatic|cdn|unpkg|jsdelivr|.*onrender)|localhost:[0-9]|/ws/|/api/tts|new WebSocket" ${JSON.stringify(dist)} --include=*.html --include=*.js --include=*.css || true`
).toString().trim();
if (offOrigin) throw new Error("Off-origin reference in shipped code:\n" + offOrigin);

// Build the flat zip.
fs.rmSync(zip, { force: true });
execSync(`cd ${JSON.stringify(dist)} && zip -r -q ${JSON.stringify(zip)} .`);

const files = execSync(`cd ${JSON.stringify(dist)} && find . -type f | wc -l`).toString().trim();
const size = fs.statSync(zip).size;
console.log(`Built ${zip}`);
console.log(`  ${files} files, ${(size / 1048576).toFixed(2)} MB, index.html at root, no secrets, no off-origin refs.`);
