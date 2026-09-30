// Port of extract_landmarks_new() from asl-detector/landmarks.py
// Input: array of 21 objects with numeric .x .y .z (MediaPipe tasks-vision landmark)
// Output: Float32Array(63) = flattened [x0,y0,z0, x1,y1,z1, ...]
// Normalization: translate to wrist (index 0), scale by max L2 distance from wrist.
export function extractLandmarks(landmarks) {
  const coords = new Array(21);
  const wx = landmarks[0].x, wy = landmarks[0].y, wz = landmarks[0].z;
  let maxDist = 0;
  for (let i = 0; i < 21; i++) {
    const x = landmarks[i].x - wx;
    const y = landmarks[i].y - wy;
    const z = landmarks[i].z - wz;
    coords[i] = [x, y, z];
    const d = Math.sqrt(x * x + y * y + z * z);
    if (d > maxDist) maxDist = d;
  }
  const out = new Float32Array(63);
  for (let i = 0; i < 21; i++) {
    const [x, y, z] = coords[i];
    if (maxDist > 0) {
      out[i * 3] = x / maxDist;
      out[i * 3 + 1] = y / maxDist;
      out[i * 3 + 2] = z / maxDist;
    } else {
      out[i * 3] = x; out[i * 3 + 1] = y; out[i * 3 + 2] = z;
    }
  }
  return out;
}
