// Port of PredictionSmoother from test-backend/asl_handler.py.
// prediction is an integer class index or null; returns [accepted|null, conf].
export class PredictionSmoother {
  constructor({ windowSize = 12, stableCount = 8, cooldown = 15, confidenceThreshold = 0.65 } = {}) {
    this.windowSize = windowSize;
    this.stableCount = stableCount;
    this.cooldown = cooldown;
    this.confidenceThreshold = confidenceThreshold;
    this.window = [];
    this.cooldownCounter = 0;
    this.lastAccepted = null;
  }

  _push(v) {
    this.window.push(v);
    if (this.window.length > this.windowSize) this.window.shift();
  }

  update(prediction, confidence) {
    if (this.cooldownCounter > 0) {
      this.cooldownCounter -= 1;
      if (this.cooldownCounter === 0) this.lastAccepted = null;
    }

    if (confidence < this.confidenceThreshold) {
      this._push(null);
      return [null, 0];
    }

    this._push(prediction);

    if (this.window.length >= this.stableCount) {
      const recent = this.window.filter((p) => p !== null);
      if (recent.length >= this.stableCount) {
        const counts = new Map();
        for (const p of recent) counts.set(p, (counts.get(p) || 0) + 1);
        let mostCommon = null, count = 0;
        for (const [k, c] of counts) if (c > count) { mostCommon = k; count = c; }
        if (count >= this.stableCount && this.cooldownCounter === 0) {
          if (mostCommon !== this.lastAccepted) {
            this.lastAccepted = mostCommon;
            this.cooldownCounter = this.cooldown;
            this.window = [];
            return [mostCommon, confidence];
          }
        }
      }
    }
    return [null, 0];
  }

  reset() {
    this.window = [];
    this.cooldownCounter = 0;
    this.lastAccepted = null;
  }
}
