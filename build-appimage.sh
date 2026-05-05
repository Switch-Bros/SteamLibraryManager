#!/bin/bash
# build-appimage.sh — Build SLM AppImage
# Usage: ./build-appimage.sh
set -euo pipefail

cd "$(dirname "$0")"
echo "Building SteamLibraryManager AppImage..."

# Clean previous builds
rm -rf AppDir dist build SteamLibraryManager-*.AppImage

# 1. Bundle with PyInstaller (--windowed, NOT --onefile — linuxdeploy needs a directory)
pip install --break-system-packages pyinstaller 2>/dev/null || pip install pyinstaller
pyinstaller \
    --name SteamLibraryManager \
    --windowed \
    --noconfirm \
    --add-data "steam_library_manager:steam_library_manager" \
    steam_library_manager/main.py

# 2. Create AppDir structure
mkdir -p AppDir/usr/{bin,share/{applications,icons/hicolor/scalable/apps,metainfo}}

# Copy PyInstaller output
cp -r dist/SteamLibraryManager/* AppDir/usr/bin/
# Symlink so linuxdeploy finds the Exec= entry from the desktop file
ln -sf SteamLibraryManager AppDir/usr/bin/steam-library-manager

# Copy desktop integration files
cp flatpak/io.github.switch_bros.SteamLibraryManager.desktop \
    AppDir/usr/share/applications/
cp flatpak/io.github.switch_bros.SteamLibraryManager.svg \
    AppDir/usr/share/icons/hicolor/scalable/apps/
cp steam_library_manager/resources/io.github.switch_bros.SteamLibraryManager.metainfo.xml \
    AppDir/usr/share/metainfo/

# AppRun needs these at the top level too
cp flatpak/io.github.switch_bros.SteamLibraryManager.desktop AppDir/
cp flatpak/io.github.switch_bros.SteamLibraryManager.svg AppDir/

# 3. Download linuxdeploy (if not cached)
LINUXDEPLOY="linuxdeploy-x86_64.AppImage"
if [ ! -f "$LINUXDEPLOY" ]; then
    wget -q "https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/${LINUXDEPLOY}"
    chmod +x "$LINUXDEPLOY"
fi

# 4. Build AppImage
# Bundle libxcb-cursor.so.0 - Qt 6.5+ needs it for the xcb platform plugin,
# and older Debian/Ubuntu/Mint don't ship it by default (GH #13).
XCB_CURSOR=$(ldconfig -p | awk '/libxcb-cursor\.so\.0/ {print $NF; exit}')
if [ -z "$XCB_CURSOR" ] || [ ! -f "$XCB_CURSOR" ]; then
    echo "ERROR: libxcb-cursor.so.0 not found on build host - install libxcb-cursor0" >&2
    exit 1
fi

ARCH=x86_64 ./"$LINUXDEPLOY" \
    --appdir AppDir \
    --desktop-file AppDir/io.github.switch_bros.SteamLibraryManager.desktop \
    --icon-file AppDir/io.github.switch_bros.SteamLibraryManager.svg \
    --library "$XCB_CURSOR" \
    --output appimage

RESULT=$(ls SteamLibraryManager-*.AppImage 2>/dev/null)
echo ""
echo "AppImage created: ${RESULT}"
echo "Test with: ./${RESULT}"
