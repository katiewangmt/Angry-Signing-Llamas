import { createHandLandmarker } from "./handLandmarker.js";
import { extractLandmarks } from "./preprocess.js";
import { loadModels } from "./models.js";
import { PredictionSmoother } from "./smoother.js";
import { ASL_LABELS, SEQUENCE_LABELS, WORD_TO_LETTER } from "./labels.js";

const SEQUENCE_LENGTH = 30;
const PREDICTION_INTERVAL = 1;
const FRAME_INTERVAL_MS = 33; // throttle detection to ~30fps to match LSTM training capture rate

export async function createEngine({ video, onMessage }) {
  const hl = await createHandLandmarker();
  const models = await loadModels();
  const flipCanvas = document.createElement("canvas");
  const flipCtx = flipCanvas.getContext("2d");

  let mode = "letters";
  let running = false;
  let lastProcessMs = 0;
  let frameCount = 0;
  let rafId = null;

  const letterSmoother = new PredictionSmoother({ windowSize: 8, stableCount: 4, cooldown: 8, confidenceThreshold: 0.65 });
  const wordSmoother = new PredictionSmoother({ windowSize: 8, stableCount: 3, cooldown: 10, confidenceThreshold: 0.3 });
  let wordBuffer = [];

  function setMode(m) {
    if (m === "letters" || m === "words" || m === "both") {
      mode = m;
      letterSmoother.reset();
      wordSmoother.reset();
      wordBuffer = [];
    }
  }

  function processFrame() {
    if (!running) return;
    rafId = requestAnimationFrame(processFrame);

    const now = performance.now();
    if (now - lastProcessMs < FRAME_INTERVAL_MS) return;
    lastProcessMs = now;
    frameCount += 1;

    const hand = hl.detectForVideo(video, now, flipCanvas, flipCtx);
    const handDetected = !!hand;
    const vec = handDetected ? extractLandmarks(hand) : null;

    // status message (landmarks are the flipped-frame coords, [x,y] pairs)
    const status = { type: "status", hand_detected: handDetected };
    if (handDetected) status.landmarks = hand.map((lm) => [lm.x, lm.y]);
    onMessage(status);

    // letters
    if ((mode === "letters" || mode === "both")) {
      if (handDetected && vec) {
        const { index, confidence } = models.predictStatic(vec);
        const [accepted, conf] = letterSmoother.update(index, confidence);
        if (accepted !== null) {
          onMessage({ type: "detection", kind: "letter", value: ASL_LABELS[accepted], confidence: Math.round(conf * 1000) / 1000 });
        }
      } else {
        letterSmoother.update(null, 0);
      }
    }

    // words
    if ((mode === "words" || mode === "both")) {
      if (handDetected && vec) {
        wordBuffer.push(Array.from(vec));
      } else if (wordBuffer.length > 0) {
        wordBuffer.push(wordBuffer[wordBuffer.length - 1]);
      }
      if (wordBuffer.length > SEQUENCE_LENGTH) wordBuffer.shift();

      let wordPred = null, wordConf = 0;
      if (wordBuffer.length === SEQUENCE_LENGTH && frameCount % PREDICTION_INTERVAL === 0) {
        const r = models.predictSequence(wordBuffer);
        wordPred = r.index; wordConf = r.confidence;
      }
      const [accepted, conf] = wordPred !== null
        ? wordSmoother.update(wordPred, wordConf)
        : wordSmoother.update(null, 0);
      if (accepted !== null) {
        const wordName = SEQUENCE_LABELS[accepted];
        const display = WORD_TO_LETTER[wordName] || wordName;
        const c = Math.round(conf * 1000) / 1000;
        if (display === "DELETE") onMessage({ type: "detection", kind: "word", value: "DELETE", word: "DELETE", confidence: c });
        else if (display === "SPACE") onMessage({ type: "detection", kind: "word", value: "SPACE", word: "SPACE", confidence: c });
        else onMessage({ type: "detection", kind: "word", value: display, word: wordName, confidence: c });
      }
    }
  }

  return {
    start() { if (running) return; running = true; lastProcessMs = 0; frameCount = 0; rafId = requestAnimationFrame(processFrame); },
    stop() { running = false; if (rafId) cancelAnimationFrame(rafId); rafId = null; },
    setMode,
  };
}
