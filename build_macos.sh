#!/bin/bash
# Build the macOS app and DMG. Run on a Mac (Apple Silicon or Intel) with Python 3.11:
#   chmod +x build_macos.sh && ./build_macos.sh
set -e
cd "$(dirname "$0")"
python3 -m pip install -r requirements.txt pyinstaller pytest pillow markdown pymupdf
python3 -m pytest tests -q
python3 tools/build_manuals.py
python3 -m PyInstaller --noconfirm --clean fcp_live_analyzer_macos.spec
# headless self-test of the bundled app
"dist/FCP Live Analyzer.app/Contents/MacOS/FCP Live Analyzer" --selftest /tmp/fcp_selftest.json
cat /tmp/fcp_selftest.json
ARCH=$(uname -m)
DMG="dist/FCP_Live_Analyzer_2.0.0_macOS_${ARCH}.dmg"
rm -f "$DMG"
mkdir -p dist/dmg && rm -rf dist/dmg/* && cp -R "dist/FCP Live Analyzer.app" dist/dmg/ && ln -s /Applications dist/dmg/Applications
cp docs/Manual_FCP_Live_Analyzer_EN.pdf docs/Manual_FCP_Live_Analyzer_pt-BR.pdf LICENSE NOTICE dist/dmg/
hdiutil create -volname "FCP Live Analyzer 2.0.0" -srcfolder dist/dmg -ov -format UDZO "$DMG"
echo "OK: $DMG"
