"""
DEBUG VERSION - Shows detailed errors
Pure Python Server for ASL to Rap Speech (No pip needed!)
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse
import ssl
import traceback

# ElevenLabs API Configuration
ELEVENLABS_API_KEY = "0bbe00bc30909760c07ccaf8a4b5391e134f9a4972761478782f92a6f20fba5d"
ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"

# HTML content with better error messages
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ASL to Rap Speech 🎤 [DEBUG]</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            padding: 40px;
            max-width: 800px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }
        h1 { color: #667eea; text-align: center; margin-bottom: 10px; font-size: 2.5em; }
        .subtitle { text-align: center; color: #666; margin-bottom: 30px; font-size: 1.1em; }
        .input-section { margin-bottom: 30px; }
        label { display: block; margin-bottom: 10px; color: #333; font-weight: 600; }
        textarea {
            width: 100%;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 16px;
            font-family: inherit;
            resize: vertical;
            min-height: 120px;
        }
        .settings-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .setting-item { display: flex; flex-direction: column; }
        .range-value { text-align: center; color: #667eea; font-weight: 600; margin-top: 5px; }
        select { padding: 10px; border: 2px solid #e0e0e0; border-radius: 10px; font-size: 16px; }
        .button-group { display: flex; gap: 15px; margin-bottom: 20px; }
        button {
            flex: 1;
            padding: 15px 30px;
            font-size: 18px;
            font-weight: 600;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .generate-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .generate-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .clear-btn { background: #e0e0e0; color: #333; }
        .audio-player {
            margin-top: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            display: none;
        }
        .audio-player.active { display: block; }
        audio { width: 100%; margin-top: 10px; }
        .status {
            padding: 15px;
            border-radius: 10px;
            margin-top: 20px;
            display: none;
            white-space: pre-wrap;
            font-family: monospace;
            font-size: 12px;
        }
        .status.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
            display: block;
        }
        .status.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
            display: block;
        }
        .loading { text-align: center; padding: 20px; display: none; }
        .loading.active { display: block; }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 10px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .debug-box {
            background: #fff3cd;
            border: 1px solid #ffc107;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            font-size: 14px;
        }
        .download-btn { background: #28a745; color: white; margin-top: 10px; width: 100%; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎤 ASL to Rap Speech [DEBUG MODE]</h1>
        <p class="subtitle">Debug version with detailed error messages</p>
        
        <div class="debug-box">
            <strong>🔍 Debug Info:</strong>
            <div id="debugInfo">Server connected. Ready to generate speech.</div>
        </div>
        
        <div class="input-section">
            <label for="aslText">ASL Recognized Text:</label>
            <textarea id="aslText">Yo, breaking barriers with my hands. Sign language to rap, that's the master plan!</textarea>
        </div>
        
        <div class="settings-grid">
            <div class="setting-item">
                <label for="voiceSelect">Voice:</label>
                <select id="voiceSelect">
                    <option value="pNInz6obpgDQGcFmaJgB">Adam (Energetic)</option>
                    <option value="ErXwobaYiN019PkySvjV">Antoni</option>
                    <option value="TxGEqnHWrfWFTfGW9XjX">Josh (Deep)</option>
                </select>
            </div>
            <div class="setting-item">
                <label for="stability">Stability: <span class="range-value" id="stabilityValue">0.4</span></label>
                <input type="range" id="stability" min="0" max="1" step="0.1" value="0.4">
            </div>
            <div class="setting-item">
                <label for="style">Style: <span class="range-value" id="styleValue">0.85</span></label>
                <input type="range" id="style" min="0" max="1" step="0.05" value="0.85">
            </div>
        </div>
        
        <div class="button-group">
            <button class="generate-btn" id="generateBtn">🎵 Generate Rap Vocals</button>
            <button class="clear-btn" id="clearBtn">🗑️ Clear</button>
        </div>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>Calling ElevenLabs API...</p>
        </div>
        
        <div class="status" id="status"></div>
        
        <div class="audio-player" id="audioPlayer">
            <h3>🔊 Generated Audio:</h3>
            <audio id="audio" controls></audio>
            <button class="download-btn" id="downloadBtn">⬇️ Download MP3</button>
        </div>
    </div>
    
    <script>
        let currentAudioUrl = null;
        
        function log(msg) {
            console.log(msg);
            document.getElementById('debugInfo').innerHTML += '<br>' + msg;
        }
        
        document.getElementById('stability').addEventListener('input', (e) => {
            document.getElementById('stabilityValue').textContent = e.target.value;
        });
        
        document.getElementById('style').addEventListener('input', (e) => {
            document.getElementById('styleValue').textContent = e.target.value;
        });
        
        document.getElementById('generateBtn').addEventListener('click', async () => {
            const text = document.getElementById('aslText').value.trim();
            
            if (!text) {
                showStatus('⚠️ Please enter some text!', 'error');
                return;
            }
            
            const voiceId = document.getElementById('voiceSelect').value;
            const stability = parseFloat(document.getElementById('stability').value);
            const style = parseFloat(document.getElementById('style').value);
            
            log('Starting generation...');
            log('Text length: ' + text.length);
            log('Voice ID: ' + voiceId);
            
            document.getElementById('loading').classList.add('active');
            document.getElementById('generateBtn').disabled = true;
            document.getElementById('status').style.display = 'none';
            document.getElementById('audioPlayer').classList.remove('active');
            
            try {
                log('Sending POST request to /generate...');
                
                const response = await fetch('/generate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({text, voice_id: voiceId, stability, style})
                });
                
                log('Response status: ' + response.status);
                log('Response headers: ' + JSON.stringify([...response.headers]));
                
                if (response.ok) {
                    log('Response OK, getting blob...');
                    const audioBlob = await response.blob();
                    log('Blob size: ' + audioBlob.size + ' bytes');
                    log('Blob type: ' + audioBlob.type);
                    
                    if (audioBlob.size === 0) {
                        showStatus('❌ Error: Audio file is empty (0 bytes)\\n\\nCheck server console for errors.', 'error');
                        return;
                    }
                    
                    if (currentAudioUrl) {
                        URL.revokeObjectURL(currentAudioUrl);
                    }
                    
                    currentAudioUrl = URL.createObjectURL(audioBlob);
                    log('Audio URL created: ' + currentAudioUrl.substring(0, 50) + '...');
                    
                    const audioElement = document.getElementById('audio');
                    audioElement.src = currentAudioUrl;
                    
                    document.getElementById('audioPlayer').classList.add('active');
                    showStatus('✅ Audio generated successfully!\\n\\nSize: ' + audioBlob.size + ' bytes\\nType: ' + audioBlob.type, 'success');
                    
                    log('Attempting to play...');
                    audioElement.play()
                        .then(() => log('Playback started'))
                        .catch(e => {
                            log('Autoplay prevented: ' + e.message);
                            showStatus('✅ Audio ready! Click the play button to listen.', 'success');
                        });
                } else {
                    const errorText = await response.text();
                    log('Error response: ' + errorText);
                    showStatus('❌ Server Error (Status ' + response.status + '):\\n\\n' + errorText, 'error');
                }
            } catch (error) {
                log('JavaScript error: ' + error.message);
                log('Stack: ' + error.stack);
                showStatus('❌ Error: ' + error.message + '\\n\\nCheck browser console (F12) for details.', 'error');
            } finally {
                document.getElementById('loading').classList.remove('active');
                document.getElementById('generateBtn').disabled = false;
            }
        });
        
        document.getElementById('downloadBtn').addEventListener('click', () => {
            if (currentAudioUrl) {
                const a = document.createElement('a');
                a.href = currentAudioUrl;
                a.download = 'asl_rap_' + Date.now() + '.mp3';
                a.click();
                log('Download initiated');
            }
        });
        
        document.getElementById('clearBtn').addEventListener('click', () => {
            document.getElementById('aslText').value = '';
            document.getElementById('audioPlayer').classList.remove('active');
            document.getElementById('status').style.display = 'none';
            document.getElementById('debugInfo').innerHTML = 'Cleared. Ready for new generation.';
        });
        
        function showStatus(message, type) {
            const statusDiv = document.getElementById('status');
            statusDiv.textContent = message;
            statusDiv.className = 'status ' + type;
        }
        
        log('Page loaded successfully');
    </script>
</body>
</html>
"""


class RequestHandler(BaseHTTPRequestHandler):
    """Handle HTTP requests with detailed logging"""
    
    def do_GET(self):
        """Handle GET requests - serve the HTML page"""
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode())
            print("✅ Served HTML page")
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def do_POST(self):
        """Handle POST requests - generate speech"""
        if self.path == '/generate':
            try:
                print("\n" + "="*70)
                print("🎤 NEW REQUEST - Generating Speech")
                print("="*70)
                
                # Get request data
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode())
                
                text = data.get('text', '')
                voice_id = data.get('voice_id', 'pNInz6obpgDQGcFmaJgB')
                stability = data.get('stability', 0.4)
                style = data.get('style', 0.85)
                
                print(f"📝 Text: '{text[:100]}...'")
                print(f"🎙️  Voice ID: {voice_id}")
                print(f"⚙️  Stability: {stability}, Style: {style}")
                
                if not text:
                    print("❌ ERROR: No text provided")
                    self.send_error(400, 'No text provided')
                    return
                
                # Call ElevenLabs API
                url = f"{ELEVENLABS_BASE_URL}/text-to-speech/{voice_id}"
                print(f"🌐 Calling: {url}")
                
                payload = json.dumps({
                    "text": text,
                    "model_id": "eleven_turbo_v2_5",
                    "voice_settings": {
                        "stability": stability,
                        "similarity_boost": 0.75,
                        "style": style,
                        "use_speaker_boost": True
                    }
                }).encode()
                
                headers = {
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                    "xi-api-key": ELEVENLABS_API_KEY
                }
                
                print("📡 Sending request to ElevenLabs...")
                
                # Create request
                req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
                
                # Disable SSL verification (for some Windows systems)
                context = ssl._create_unverified_context()
                
                # Make API call
                with urllib.request.urlopen(req, context=context, timeout=30) as response:
                    audio_data = response.read()
                    
                    print(f"✅ SUCCESS! Received {len(audio_data):,} bytes of audio")
                    print(f"📊 Content-Type: {response.headers.get('Content-Type')}")
                    
                    if len(audio_data) == 0:
                        print("⚠️  WARNING: Audio data is empty!")
                        self.send_error(500, 'Received empty audio data from API')
                        return
                    
                    # Send audio back to browser
                    self.send_response(200)
                    self.send_header('Content-type', 'audio/mpeg')
                    self.send_header('Content-Length', str(len(audio_data)))
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Cache-Control', 'no-cache')
                    self.end_headers()
                    self.wfile.write(audio_data)
                    
                    print("✅ Audio sent to browser")
                    print("="*70 + "\n")
                    
            except urllib.error.HTTPError as e:
                error_body = e.read().decode()
                print(f"\n❌ ElevenLabs API ERROR:")
                print(f"   Status: {e.code}")
                print(f"   Response: {error_body}")
                print("="*70 + "\n")
                
                self.send_response(e.code)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"ElevenLabs API Error {e.code}: {error_body}".encode())
                
            except urllib.error.URLError as e:
                print(f"\n❌ NETWORK ERROR:")
                print(f"   {e.reason}")
                print("   Make sure you have internet connection!")
                print("="*70 + "\n")
                
                self.send_response(503)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Network Error: {e.reason}".encode())
                
            except Exception as e:
                print(f"\n❌ UNEXPECTED ERROR:")
                print(f"   {type(e).__name__}: {e}")
                print(f"\n   Traceback:")
                traceback.print_exc()
                print("="*70 + "\n")
                
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Server Error: {type(e).__name__}: {e}".encode())
        else:
            self.send_error(404)
    
    def log_message(self, format, *args):
        """Custom logging"""
        return


def run_server(port=8000):
    """Start the HTTP server"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, RequestHandler)
    
    print("\n" + "="*70)
    print("  🎤 ASL to Rap Speech Server [DEBUG MODE]")
    print("="*70)
    print(f"\n✅ Server running on http://localhost:{port}")
    print(f"📱 Open your browser and go to: http://localhost:{port}")
    print("\n📋 This debug version shows detailed error messages")
    print("   Check this console window for server-side logs")
    print("\n⌨️  Press Ctrl+C to stop the server\n")
    print("="*70 + "\n")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped")
        httpd.shutdown()


if __name__ == '__main__':
    # Try different ports
    for port in [8000, 8080, 5000, 3000]:
        try:
            run_server(port)
            break
        except OSError as e:
            if "Address already in use" in str(e):
                print(f"⚠️  Port {port} is busy, trying next port...")
                continue
            else:
                raise
