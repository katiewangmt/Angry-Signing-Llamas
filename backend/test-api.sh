#!/bin/sh
# Quick API test when the server is running on port 5000.
# Usage: ./test-api.sh   (start the backend first: ./mvnw spring-boot:run)

set -e
URL="${1:-http://localhost:5000/api/random-music}"
echo "Testing GET $URL ..."
STATUS=$(curl -s -o /tmp/random-music-test.wav -w "%{http_code}" "$URL")
if [ "$STATUS" = "200" ]; then
  SIZE=$(wc -c < /tmp/random-music-test.wav)
  echo "OK: status 200, size $SIZE bytes (saved to /tmp/random-music-test.wav)"
  head -c 4 /tmp/random-music-test.wav | od -A n -t x1 | grep -q "52 49 46 46" && echo "OK: WAV header (RIFF) present" || echo "WARN: header might not be WAV"
else
  echo "FAIL: status $STATUS (expected 200). Is the backend running? Try: ./mvnw spring-boot:run"
  exit 1
fi
