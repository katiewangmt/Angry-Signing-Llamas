# ASL Freestyle frontend

- **Camera + hand landmarks:** “Start camera” uses your webcam and draws 21 hand landmarks (MediaPipe in the browser). “Stop camera” turns it off.
- **Random music:** “Play random music” and “Pause” call the Java backend.

## Easiest: use the backend’s page (no port 3000)

1. Start the backend:
   ```bash
   cd backend-java
   mvn spring-boot:run
   ```
2. Open in your browser: **http://localhost:5000**

The same app (camera + music) is served there. You don’t need to run anything on port 3000.

## Optional: run this folder separately

If you want to serve this `frontend/` folder on another port (e.g. 3000):

```bash
npx serve frontend -p 3000
```

Then open **http://localhost:3000**. The page will call the backend at `http://localhost:5000` (CORS is allowed). If port 3000 doesn’t open, use **http://localhost:5000** instead (see above).

**Camera:** Allow camera access when the browser prompts. Hand landmarks load from MediaPipe’s CDN.
