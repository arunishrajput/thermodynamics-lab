#!/bin/bash
set -e

echo "============================================================"
echo " Thermodynamics Lab — macOS App Builder"
echo "============================================================"
echo ""

echo "[1/3] Installing Python dependencies..."
pip install -r requirements.txt pyinstaller

echo ""
echo "[2/3] Building .app bundle (this takes ~1-2 minutes)..."
pyinstaller --clean ThermodynamicsLab.spec

echo ""
echo "[3/3] Packaging into a zip..."
ditto -c -k --keepParent dist/ThermodynamicsLab.app dist/ThermodynamicsLab-macOS.zip

echo ""
echo "  App:  dist/ThermodynamicsLab.app"
echo "  Zip:  dist/ThermodynamicsLab-macOS.zip"
echo ""
echo "  First run: right-click the .app → Open (bypasses Gatekeeper)"
echo "  Plug in your Arduino before launching."
