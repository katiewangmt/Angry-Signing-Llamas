# ASL Freestyle Backend (Java)

Random music on button click, pause in the browser. **No external music API** — music is generated in code (`MusicGenerator.java`). Generated WAVs are saved in `generated/`.

## Is it complete?

Yes. The backend generates music itself and serves a simple frontend (Play / Pause). You don’t need any music-generating API.

## How does the frontend connect?

**Option A — Built-in frontend (already connected)**  
When you run the app and open **http://localhost:5000**, you get the page that’s in `src/main/resources/static/index.html`. That page already calls `GET /api/random-music` and has Play / Pause. Nothing else to connect.

**Option B — Separate frontend (e.g. React, Vue)**  
1. Run this backend: `mvn spring-boot:run` (port 5000).  
2. In your frontend app, request the API: `fetch('http://localhost:5000/api/random-music')` and use the response as the `src` for an `<audio>` element (e.g. create an object URL from the blob).  
3. CORS is enabled for `http://localhost:3000` and `http://127.0.0.1:3000`. If your app runs on another port, add it in `WebConfig.java` (`allowedOrigins`).

## Requirements

- **Java 17** (required). Install with `brew install openjdk@17` on Mac if you see "Unable to locate a Java Runtime". See **RUN.md** for details.
- Maven is not required; the project includes `./mvnw`.

## Run

**You don’t need to install Maven.** Use the wrapper script instead:

```bash
cd /Users/wenningcikeshangan/cs_/ADI2026/backend-java
./mvnw spring-boot:run
```

The first run will download Maven into `.mvn/cache` (one-time). If you prefer to install Maven globally, you can run `mvn spring-boot:run` instead. See **RUN.md** for more detail. To test without running the server: **./mvnw test**. See **TESTING.md** for all ways to test the API.

Then open **http://localhost:5000** in your browser. You get the full app: **camera + hand landmarks** and **Play random music** / **Pause**. No need to open port 3000.

## Generated files

Each time you click "Play random music", a new file is written to:

**`backend-java/generated/random_yyyyMMdd_HHmmss.wav`**

(Relative to where you started the app; if you run from project root, the folder may be at project root.)
