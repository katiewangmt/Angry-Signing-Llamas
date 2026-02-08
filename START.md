# How to Run SignCraft Web App

## Quick Start (Easiest Method)

### Using the Startup Scripts

**Terminal 1 - Backend:**
```bash
cd ADI
./start-backend.sh
```

**Terminal 2 - Frontend:**
```bash
cd ADI
./start-frontend.sh
```

Then open **http://localhost:3000** in your browser.

---

## Manual Start

### 1. Start the Backend Server

Open a terminal and run:

```bash
cd ADI/test-backend
pip install -r requirements.txt

# Development (auto-reloads on code changes):
uvicorn server:app --reload --port 8000

# Production:
uvicorn server:app --host 0.0.0.0 --port 8000 --workers 4
```

The backend will start on `http://localhost:8000`

### 2. Start the Frontend

Open another terminal and run:

```bash
cd ADI/frontend
# Option 1: Using Python's built-in server
python3 -m http.server 3000
# or
python -m http.server 3000

# Option 2: Using npx serve (if you have Node.js)
npx serve . -p 3000
```

### 3. Open in Browser

Open your browser and go to:
- **http://localhost:3000** (or the port you chose)

## What You'll See

- **Live Feed**: Webcam feed with ASL detection
- **Detected Signs**: Real-time letter/word detection
- **ASL Alphabet Tutorial**: Scrollable grid showing all 26 letters with sign images
- **Beat Generator**: (Optional) Music generation feature

## Troubleshooting

### Backend Issues
- Make sure TensorFlow models are in `ADI/asl-detector/`:
  - `asl_model.keras` (for letters)
  - `asl_lstm_model.keras` (for words)
- Check that all dependencies are installed: `pip install -r requirements.txt`

### Frontend Issues
- Make sure the backend is running on port 8000
- Check browser console for CORS errors
- Allow camera access when prompted

### Port Conflicts
- If port 8000 is taken, change the backend port and update `API_BASE` in `frontend/index.html`
- If port 3000 is taken, use a different port for the frontend server

