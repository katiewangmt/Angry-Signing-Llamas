#!/bin/bash
# setup.sh — Quick setup for the ASL Detector project
# Usage: bash setup.sh

echo "======================================"
echo "  🤟 ASL Detector — Quick Setup"
echo "======================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required. Install it first."
    exit 1
fi

echo "📦 Installing dependencies..."
pip install tensorflow mediapipe opencv-python numpy scikit-learn --quiet

echo ""
echo "✅ Setup complete! Here's your workflow:"
echo ""
echo "  Step 1: Collect data    →  python3 collect_data.py"
echo "  Step 2: Train model     →  python3 train_model.py"
echo "  Step 3: Run detector    →  python3 detect.py"
echo ""
echo "🚀 Start with: python3 collect_data.py"
