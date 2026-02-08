# How to Run SignCraft (Hackathon Mode)

SignCraft runs as **one server**: the backend serves the frontend + websockets + ASL.

## Quick Start (recommended)

From the repo root:

```bash
chmod +x run_local.sh
./run_local.sh
```

Open: `http://localhost:8000`

## “Professional demo” (public HTTPS link, still fast)

This keeps ASL running on your laptop CPU (fast), but gives you a shareable URL for judges.

1) Install Cloudflare Tunnel:

- **macOS**:

```bash
brew install cloudflare/cloudflare/cloudflared
```

- **Windows**:

```bash
winget install Cloudflare.cloudflared
```

2) Run:

```bash
chmod +x share_public.sh
./share_public.sh
```

Copy the `https://*.trycloudflare.com` URL from the terminal and use it for your demo.

## Environment variables

### Beat generator (optional)

Create `test-backend/.env` (do not commit it) with:

```bash
GEMINI_API_KEY='your-key-here'
```

## Troubleshooting

- **No webcam**: allow camera permissions in the browser
- **Port in use**: set a different port:

```bash
PORT=8010 ./run_local.sh
```

