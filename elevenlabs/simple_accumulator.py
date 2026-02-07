"""
Simple Real-time ASL Accumulator
Continuously adds words and auto-generates speech
"""

import requests
import time
import sys

class SimpleASLAccumulator:
    def __init__(self):
        self.words = []
        self.server_url = "http://localhost:8000"
        self.auto_speak_after = 1  # Words before auto-generation (1 = instant)
        
    def add_word(self, word):
        """Add a word from your ASL recognition"""
        self.words.append(word)
        sentence = " ".join(self.words)
        
        print(f"\n📝 Added: '{word}'")
        print(f"💬 Current sentence: {sentence}")
        print(f"📊 Word count: {len(self.words)}/{self.auto_speak_after}")
        
        # Auto-generate when we reach threshold
        if len(self.words) >= self.auto_speak_after:
            self.speak()
    
    def speak(self):
        """Generate speech from accumulated words"""
        if not self.words:
            print("⚠️ No words to speak")
            return
        
        text = " ".join(self.words)
        print(f"\n🎤 Generating speech: '{text}'")
        
        try:
            response = requests.post(
                f"{self.server_url}/generate",
                json={
                    "text": text,
                    "voice_id": "pNInz6obpgDQGcFmaJgB",
                    "stability": 0.4,
                    "style": 0.85
                },
                timeout=30
            )
            
            if response.ok:
                filename = f"speech_{int(time.time())}.mp3"
                with open(filename, 'wb') as f:
                    f.write(response.content)
                print(f"✅ Saved to: {filename}")
                
                # Clear words after speaking
                self.words = []
                print("🗑️ Buffer cleared\n")
            else:
                print(f"❌ Error: {response.status_code}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def clear(self):
        """Clear all accumulated words"""
        self.words = []
        print("🗑️ Cleared!")


# Example: How to use with your YOLO code
def example_usage():
    """
    This shows how to integrate with your YOLO11 ASL recognition
    """
    accumulator = SimpleASLAccumulator()
    
    # Your YOLO code would detect words and call add_word()
    # For example:
    
    # while True:
    #     frame = get_camera_frame()
    #     results = yolo_model(frame)
    #     detected_word = extract_word(results)
    #     
    #     if detected_word:
    #         accumulator.add_word(detected_word)
    
    # DEMO with manual input:
    print("=" * 60)
    print("  Simple ASL Word Accumulator")
    print("=" * 60)
    print("\nType words one at a time (or space-separated)")
    print("Commands:")
    print("  'speak' - Generate speech now")
    print("  'clear' - Clear buffer")
    print("  'quit'  - Exit")
    print(f"\nAuto-generates instantly for each word\n")
    
    while True:
        user_input = input("Word(s): ").strip()
        
        if not user_input:
            continue
        elif user_input.lower() == 'quit':
            break
        elif user_input.lower() == 'speak':
            accumulator.speak()
        elif user_input.lower() == 'clear':
            accumulator.clear()
        else:
            # Handle multiple words
            words = user_input.split()
            for word in words:
                accumulator.add_word(word)


if __name__ == "__main__":
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:8000", timeout=2)
        print("✅ Server is running\n")
    except:
        print("❌ ERROR: Server not running!")
        print("Please start the server first:")
        print("  python debug_server.py\n")
        sys.exit(1)
    
    example_usage()
