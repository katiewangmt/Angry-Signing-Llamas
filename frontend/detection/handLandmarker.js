import { FilesetResolver, HandLandmarker } from "./vendor/mediapipe/vision_bundle.mjs";

// Wraps MediaPipe tasks-vision HandLandmarker with locally-served WASM + .task model.
export async function createHandLandmarker() {
  const fileset = await FilesetResolver.forVisionTasks("./detection/vendor/mediapipe/wasm");
  const landmarker = await HandLandmarker.createFromOptions(fileset, {
    baseOptions: { modelAssetPath: "./detection/hand_landmarker.task" },
    runningMode: "VIDEO",
    numHands: 1,
    minHandDetectionConfidence: 0.7,
    minTrackingConfidence: 0.5,
  });
  return {
    // Returns array of 21 {x,y,z} for the first hand, or null. Feeds a
    // horizontally-flipped frame to match the Python cv2.flip(frame,1).
    detectForVideo(video, timestampMs, flipCanvas, flipCtx) {
      const vw = video.videoWidth, vh = video.videoHeight;
      flipCanvas.width = vw; flipCanvas.height = vh;
      flipCtx.save();
      flipCtx.translate(vw, 0); flipCtx.scale(-1, 1);
      flipCtx.drawImage(video, 0, 0, vw, vh);
      flipCtx.restore();
      const res = landmarker.detectForVideo(flipCanvas, timestampMs);
      if (res.landmarks && res.landmarks.length > 0) return res.landmarks[0];
      return null;
    },
  };
}
