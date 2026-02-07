# How to test the API and code

## 1. Run unit + integration tests (no server needed)

With **Java 17** installed:

```bash
cd /Users/wenningcikeshangan/cs_/ADI2026/backend-java
./mvnw test
```

This runs:

- **MusicGeneratorTest** – WAV generation returns valid bytes and header; different calls give different music.
- **MusicControllerTest** – `GET /api/random-music` returns 200 and `audio/wav` (full Spring context, no manual server).

If all tests pass, the core logic and API contract are working. Safe to push.

---

## 2. Test the API while the server is running

Start the backend in one terminal:

```bash
cd /Users/wenningcikeshangan/cs_/ADI2026/backend-java
./mvnw spring-boot:run
```

Then in another terminal (or after the server has started):

**Option A – Script (saves a WAV file):**
```bash
cd /Users/wenningcikeshangan/cs_/ADI2026/backend-java
./test-api.sh
```

**Option B – curl:**
```bash
curl -o test.wav http://localhost:5000/api/random-music
# Check: file test.wav  →  should say "RIFF ... WAVE audio"
# Play it (Mac): afplay test.wav
```

**Option C – Browser:**  
Open **http://localhost:5000** and use “Play random music” and “Pause”.

---

## 3. Push and let CI run tests (optional)

If you use **GitHub**, add a workflow so tests run on push. Create:

**.github/workflows/build.yml** (in the repo root):

```yaml
name: Build and test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '17'
      - name: Run tests
        run: |
          cd backend-java
          ./mvnw test -q
```

Then every push runs the tests in the cloud; you don’t need Java on your machine to know they pass.

---

## Summary

| Goal                         | Command / action                          |
|-----------------------------|-------------------------------------------|
| Test code without running server | `./mvnw test`                        |
| Test API with server running    | `./test-api.sh` or curl or browser  |
| Verify after push (CI)          | Add `.github/workflows/build.yml` above   |
