"""
Real-time ASL to Speech Integration
Continuously monitors ASL recognition and generates speech automatically
"""

import cv2
import requests
import time
import json
from collections import deque
import threading

class RealtimeASLToSpeech:
    """
    Real-time ASL recognition to speech converter
    Accumulates words and auto-generates speech when conditions are met
    """
    
    def __init__(self, server_url="http://localhost:8000"):
        self.server_url = server_url
        self.word_buffer = deque(maxlen=50)  # Store last 50 words
        self.current_sentence = ""
        self.last_generation_time = 0
        self.generation_cooldown = 3  # seconds between generations
        self.is_generating = False
        
        # Settings
        self.words_per_phrase = 1  # Generate speech every N words (1 = instant)
        self.auto_generate = True
        
    def add_word(self, word):
        """
        Add a newly recognized word from YOLO11
        
        Args:
            word: String word recognized from ASL
        """
        if word and word.strip():
            self.word_buffer.append(word.strip())
            self.current_sentence = " ".join(list(self.word_buffer))
            print(f"📝 Added word: '{word}' | Current: '{self.current_sentence}'")
            
            # Auto-generate if we have enough words
            if self.auto_generate and len(self.word_buffer) >= self.words_per_phrase:
                self.generate_speech_async()
    
    def generate_speech(self, text=None, voice_id="pNInz6obpgDQGcFmaJgB"):
        """
        Generate speech for the accumulated text
        
        Args:
            text: Optional custom text (uses current_sentence if None)
            voice_id: ElevenLabs voice ID
        """
        if self.is_generating:
            print("⏳ Already generating speech, skipping...")
            return False
        
        # Check cooldown
        time_since_last = time.time() - self.last_generation_time
        if time_since_last < self.generation_cooldown:
            print(f"⏳ Cooldown active ({self.generation_cooldown - time_since_last:.1f}s remaining)")
            return False
        
        text_to_speak = text or self.current_sentence
        
        if not text_to_speak.strip():
            print("⚠️ No text to generate")
            return False
        
        self.is_generating = True
        print(f"\r\n🎤 Generating speech for: '{text_to_speak}'")
        
        try:
            response = requests.post(
                f"{self.server_url}/generate",
                json={
                    "text": text_to_speak,
                    "voice_id": voice_id,
                    "stability": 0.4,
                    "style": 0.85
                },
                timeout=30
            )
            
            if response.status_code == 200:
                # Save audio file
                filename = f"output_{int(time.time())}.mp3"
                with open(filename, 'wb') as f:
                    f.write(response.content)
                
                print(f"✅ Speech generated! Saved to: {filename}")
                print(f"📊 Audio size: {len(response.content):,} bytes")
                
                # Play the audio (optional - platform specific)
                self.play_audio(filename)
                
                # Clear buffer after successful generation
                self.word_buffer.clear()
                self.current_sentence = ""
                self.last_generation_time = time.time()
                
                return True
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error generating speech: {e}")
            return False
        finally:
            self.is_generating = False
    
    def generate_speech_async(self):
        """Generate speech in a background thread to not block video processing"""
        thread = threading.Thread(target=self.generate_speech)
        thread.daemon = True
        thread.start()
    
    def play_audio(self, filename):
        """
        Attempt to play audio file (platform-specific)
        
        Args:
            filename: Path to MP3 file
        """
        import platform
        import os
        
        system = platform.system()
        
        try:
            if system == "Windows":
                os.system(f'start {filename}')
            elif system == "Darwin":  # macOS
                os.system(f'afplay {filename}')
            elif system == "Linux":
                os.system(f'mpg123 {filename} &')
        except:
            print("🔇 Auto-play not available, file saved for manual playback")


def simulate_yolo_recognition():
    """
    EXAMPLE: Simulates YOLO11 ASL recognition
    Replace this with your actual YOLO11 model inference
    """
    # Sample words that would come from your YOLO model
    sample_words = [
        "hello", "my", "name", "is", "alex",
        "i", "love", "music", "and", "technology",
        "breaking", "barriers", "with", "sign", "language",
        "this", "is", "amazing", "rap", "vocals"
    ]
    
    index = 0
    while index < len(sample_words):
        word = sample_words[index]
        yield word
        index += 1
        time.sleep(1)  # Simulate detection delay


def example_realtime_with_webcam():
    """
    EXAMPLE: Real-time ASL recognition with webcam
    
    TODO: Replace the placeholder YOLO inference with your actual model
    """
    
    print("=" * 70)
    print("  🎤 Real-time ASL to Rap Speech")
    print("=" * 70)
    print("\r\n⚙️  Initializing...")
    
    # Initialize ASL to Speech
    asl_speech = RealtimeASLToSpeech()
    
    # Initialize webcam
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Cannot open webcam")
        return
    
    # TODO: Load your YOLO11 model here
    # from ultralytics import YOLO
    # model = YOLO('path/to/your/asl_model.pt')
    
    print("\r\n✅ System ready!")
    print("\r\n📹 Controls:")
    print("   SPACE - Manually generate speech from current words")
    print("   C     - Clear word buffer")
    print("   Q     - Quit")
    print("\r\n🎯 Auto-generation: Every 10 words\r\n")
    print("=" * 70 + "\r\n")
    
    frame_count = 0
    
    # For demo: use simulated words
    word_generator = simulate_yolo_recognition()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Process every N frames to reduce load
        if frame_count % 30 == 0:  # Every 30 frames (~1 second at 30fps)
            
            # TODO: Replace this with actual YOLO11 inference
            # results = model(frame)
            # detected_word = extract_word_from_results(results)
            
            # DEMO: Get simulated word
            try:
                detected_word = next(word_generator)
                asl_speech.add_word(detected_word)
            except StopIteration:
                pass
        
        # Display info on frame
        cv2.putText(
            frame,
            f"Words: {len(asl_speech.word_buffer)}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )
        
        cv2.putText(
            frame,
            f"Current: {asl_speech.current_sentence[:50]}...",
            (10, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1
        )
        
        if asl_speech.is_generating:
            cv2.putText(
                frame,
                "GENERATING SPEECH...",
                (10, 90),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2
            )
        
        cv2.imshow('ASL Recognition', frame)
        
        key = cv2.waitKey(1) & 0xFF
        
        # Manual generation
        if key == ord(' '):
            asl_speech.generate_speech_async()
        
        # Clear buffer
        elif key == ord('c'):
            asl_speech.word_buffer.clear()
            asl_speech.current_sentence = ""
            print("🗑️ Buffer cleared")
        
        # Quit
        elif key == ord('q'):
            break
        
        frame_count += 1
    
    cap.release()
    cv2.destroyAllWindows()
    print("\r\n✅ Session ended")


def example_text_stream():
    """
    EXAMPLE: Process text stream without video
    Useful for testing or if you're getting text from another source
    """
    
    print("=" * 70)
    print("  🎤 Text Stream to Rap Speech")
    print("=" * 70)
    print("\r\nType words and press ENTER. Speech auto-generates every 10 words.")
    print("Commands: 'generate' = force generation, 'clear' = clear buffer, 'quit' = exit\r\n")
    
    asl_speech = RealtimeASLToSpeech()
    
    while True:
        user_input = input("Enter word(s): ").strip()
        
        if user_input.lower() == 'quit':
            break
        elif user_input.lower() == 'generate':
            asl_speech.generate_speech()
        elif user_input.lower() == 'clear':
            asl_speech.word_buffer.clear()
            asl_speech.current_sentence = ""
            print("🗑️ Buffer cleared")
        elif user_input:
            # Add all words from input
            words = user_input.split()
            for word in words:
                asl_speech.add_word(word)
    
    print("✅ Done!")


def example_yolo_integration():
    """
    TEMPLATE: How to integrate with your actual YOLO11 model
    Copy this code and modify with your model
    """
    
    from ultralytics import YOLO  # You'll need: pip install ultralytics
    
    # Initialize
    asl_speech = RealtimeASLToSpeech()
    model = YOLO('path/to/your/asl_model.pt')  # Your trained ASL model
    cap = cv2.VideoCapture(0)
    
    print("🎤 Real-time ASL to Speech - YOLO11 Integration")
    print("Press Q to quit\r\n")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Run YOLO11 inference
        results = model(frame, verbose=False)
        
        # Extract recognized signs/words
        for result in results:
            if result.boxes:
                for box in result.boxes:
                    # Get the class name (the recognized ASL sign/word)
                    class_id = int(box.cls[0])
                    word = model.names[class_id]
                    confidence = float(box.conf[0])
                    
                    # Only add high-confidence detections
                    if confidence > 0.7:
                        asl_speech.add_word(word)
        
        # Display
        annotated_frame = results[0].plot()
        cv2.putText(
            annotated_frame,
            f"Buffer: {asl_speech.current_sentence[:60]}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2
        )
        
        cv2.imshow('ASL to Rap Speech', annotated_frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    print("\r\n🎤 ASL to Rap Speech - Real-time Integration\r\n")
    print("Choose an example:")
    print("1. Webcam with simulated recognition (DEMO)")
    print("2. Text stream input (TESTING)")
    print("3. Show YOLO11 integration template (CODE)")
    
    choice = input("\r\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        example_realtime_with_webcam()
    elif choice == "2":
        example_text_stream()
    elif choice == "3":
        print("\r\n" + "=" * 70)
        print("YOLO11 Integration Template:")
        print("=" * 70)
        print("""
# 1. Install YOLO
pip install ultralytics

# 2. Use this code:

from ultralytics import YOLO
from realtime_integration import RealtimeASLToSpeech
import cv2

# Initialize
asl_speech = RealtimeASLToSpeech()
model = YOLO('your_asl_model.pt')
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    results = model(frame)
    
    for result in results:
        for box in result.boxes:
            word = model.names[int(box.cls[0])]
            if float(box.conf[0]) > 0.7:
                asl_speech.add_word(word)
    
    cv2.imshow('ASL', results[0].plot())
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
        """)
    else:
        print("Invalid choice")
