# 🔄 Real-time ASL to Speech Integration Guide

## How It Works

```
YOLO11 detects sign → Word extracted → Instantly generate rap speech for that word
```

## 🚀 Quick Start (3 Steps)

### Step 1: Start the Server
In one terminal:
```bash
python debug_server.py
```
Leave this running!

### Step 2: Test the Accumulator
In another terminal:
```bash
python simple_accumulator.py
```

Type words one at a time. Speech generates **instantly** for each word!

### Step 3: Integrate with Your YOLO Model
See examples below.

---

## 📝 Integration Options

### Option 1: Simple Word-by-Word (Easiest)

```python
from simple_accumulator import SimpleASLAccumulator
import cv2

# Initialize
accumulator = SimpleASLAccumulator()
cap = cv2.VideoCapture(0)

# Your YOLO loop
while True:
    ret, frame = cap.read()
    
    # YOUR YOLO CODE HERE - detect ASL sign
    # word = your_yolo_function(frame)
    
    # Add word to accumulator
    if word:
        accumulator.add_word(word)  # Generates speech instantly!
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
```

### Option 2: Full Real-time System

```python
from realtime_integration import RealtimeASLToSpeech
from ultralytics import YOLO
import cv2

# Initialize
asl_speech = RealtimeASLToSpeech()
model = YOLO('your_asl_model.pt')
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    
    # YOLO detection
    results = model(frame)
    
    # Extract words
    for result in results:
        for box in result.boxes:
            word = model.names[int(box.cls[0])]
            confidence = float(box.conf[0])
            
            if confidence > 0.7:  # Only high-confidence
                asl_speech.add_word(word)
    
    # Display
    cv2.imshow('ASL', results[0].plot())
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
```

### Option 3: Manual HTTP Requests

```python
import requests

words = []

# In your YOLO loop:
while True:
    word = detect_asl_sign(frame)
    words.append(word)
    
    # Generate every 10 words
    if len(words) >= 10:
        text = " ".join(words)
        
        response = requests.post(
            "http://localhost:8000/generate",
            json={
                "text": text,
                "voice_id": "pNInz6obpgDQGcFmaJgB",
                "stability": 0.4,
                "style": 0.85
            }
        )
        
        # Save audio
        with open(f"speech_{time.time()}.mp3", 'wb') as f:
            f.write(response.content)
        
        words = []  # Clear buffer
```

---

## ⚙️ Configuration

### Change to Generate Multiple Words at Once

By default, speech generates instantly for each sign. To accumulate multiple words:

**simple_accumulator.py:**
```python
accumulator = SimpleASLAccumulator()
accumulator.auto_speak_after = 10  # Wait for 10 words before generating
```

**realtime_integration.py:**
```python
asl_speech = RealtimeASLToSpeech()
asl_speech.words_per_phrase = 10  # Wait for 10 words
```

### Change Voice Settings

```python
# In your code, when calling generate:
accumulator.speak()  # Uses defaults

# Or customize:
requests.post("http://localhost:8000/generate", json={
    "text": text,
    "voice_id": "pNInz6obpgDQGcFmaJgB",  # Adam (energetic)
    "stability": 0.3,  # Lower = more expressive
    "style": 0.9       # Higher = more dynamic
})
```

### Available Voices

| Voice ID | Name | Description |
|----------|------|-------------|
| `pNInz6obpgDQGcFmaJgB` | Adam | Energetic male (best for rap) |
| `ErXwobaYiN019PkySvjV` | Antoni | Well-rounded male |
| `TxGEqnHWrfWFTfGW9XjX` | Josh | Deep male voice |
| `VR6AewLTigWG4xSOukaG` | Arnold | Crisp, clear male |

---

## 🎯 How Your YOLO Integration Should Look

```python
"""
Your complete ASL to Rap Speech system
"""

from simple_accumulator import SimpleASLAccumulator
from ultralytics import YOLO
import cv2

# 1. Load your trained ASL model
model = YOLO('path/to/your/asl_yolo_model.pt')

# 2. Initialize speech accumulator
accumulator = SimpleASLAccumulator()
# Default: instant generation per word
# To wait for multiple words: accumulator.auto_speak_after = 10

# 3. Start webcam
cap = cv2.VideoCapture(0)

print("🎤 ASL to Rap Speech - Real-time")
print("Press Q to quit\n")

frame_count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    # Run YOLO detection every few frames (for performance)
    if frame_count % 5 == 0:
        
        # 4. Detect ASL signs
        results = model(frame, verbose=False)
        
        # 5. Extract recognized words
        for result in results:
            if result.boxes:
                for box in result.boxes:
                    # Get the class name (ASL sign/word)
                    class_id = int(box.cls[0])
                    word = model.names[class_id]
                    confidence = float(box.conf[0])
                    
                    # 6. Add high-confidence detections
                    if confidence > 0.75:
                        accumulator.add_word(word)
    
    # 7. Display frame with detections
    annotated = results[0].plot() if 'results' in locals() else frame
    
    # Show current sentence on screen
    cv2.putText(
        annotated,
        f"Words: {' '.join(accumulator.words)}",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 255, 0),
        2
    )
    
    cv2.imshow('ASL to Rap Speech', annotated)
    
    # Controls
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord(' '):  # Spacebar = manual generation
        accumulator.speak()
    elif key == ord('c'):  # C = clear buffer
        accumulator.clear()
    
    frame_count += 1

cap.release()
cv2.destroyAllWindows()
print("✅ Session ended")
```

---

## 🎬 Testing Without YOLO

Before integrating with YOLO, test the system:

```bash
# Terminal 1: Start server
python debug_server.py

# Terminal 2: Test accumulator
python simple_accumulator.py
```

Type these words one at a time (each will generate speech instantly):
```
hello
world
this
is
amazing
```

Each word will generate speech immediately! 🎵

---

## 📊 Flow Diagram

```
┌─────────────┐
│  Webcam     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  YOLO11     │ Detects ASL signs
│  Model      │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Extract    │ word = "hello"
│  Word       │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Accumulator │ Stores: ["hello", "my", "name", ...]
└──────┬──────┘
       │
       ▼ (when buffer reaches 10 words)
┌─────────────┐
│   HTTP      │ POST to localhost:8000/generate
│  Request    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ ElevenLabs  │ Generates rap vocals
│    API      │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   MP3       │ Saved & played automatically
│   Audio     │
└─────────────┘
```

---

## 🐛 Troubleshooting

**Want to accumulate multiple words before speaking?**
```python
accumulator.auto_speak_after = 10  # Wait for 10 words
```

**Generating too slow?**
The default (instant per word) is already the fastest setting.

**Want immediate speech per word?**
```python
accumulator.auto_speak_after = 1  # This is the default
```

**Audio files piling up?**
They're saved as `speech_timestamp.mp3`. You can delete old ones or modify the code to reuse one filename.

**YOLO detecting too many false positives?**
```python
if confidence > 0.85:  # Increase confidence threshold
    accumulator.add_word(word)
```

---

## 🎉 You're Ready!

1. ✅ Server running (`python debug_server.py`)
2. ✅ Simple accumulator tested (`python simple_accumulator.py`)
3. ✅ Now integrate with your YOLO code using examples above!

The system will automatically generate rap vocals **instantly** as you sign each word! 🎤
