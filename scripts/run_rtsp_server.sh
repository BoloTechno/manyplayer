#!/usr/bin/env bash
# ManyPlayer RTSP Test Server Launcher for CachyOS / Linux
# Runs MediaMTX RTSP server and streams live test feeds using FFmpeg

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BIN_DIR="$PROJECT_DIR/bin"
MEDIAMTX="$BIN_DIR/mediamtx"

echo "=========================================================="
echo " Starting ManyPlayer RTSP Test Server on CachyOS"
echo "=========================================================="

# 1. Check or Download MediaMTX binary
if [ ! -f "$MEDIAMTX" ]; then
    echo "Downloading MediaMTX standalone binary..."
    mkdir -p "$BIN_DIR"
    curl -L https://github.com/bluenviron/mediamtx/releases/download/v1.21.2/mediamtx_v1.21.2_linux_amd64.tar.gz | tar -xz -C "$BIN_DIR"
fi

if [ ! -x "$MEDIAMTX" ]; then
    chmod +x "$MEDIAMTX"
fi

echo "MediaMTX version: $("$MEDIAMTX" --version)"

# 2. Start MediaMTX in background
echo "Starting RTSP Server on port 8554 (TCP/UDP)..."
"$MEDIAMTX" > /dev/null 2>&1 &
SERVER_PID=$!

# Trap cleanup on Ctrl+C
cleanup() {
    echo ""
    echo "Stopping RTSP Server and publishers..."
    kill $SERVER_PID 2>/dev/null
    kill $(jobs -p) 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

sleep 1

# 3. Broadcast test camera feeds (cam1, cam2, etc.) using FFmpeg testsrc
echo "Publishing live test RTSP streams to 127.0.0.1:8554..."
for i in {1..4}; do
    ffmpeg -re -f lavfi -i "testsrc=size=640x360:rate=15" \
        -vcodec libx264 -preset ultrafast -tune zerolatency -pix_fmt yuv420p \
        -f rtsp -rtsp_transport tcp "rtsp://127.0.0.1:8554/live/cam${i}_sub" > /dev/null 2>&1 &
    ffmpeg -re -f lavfi -i "testsrc=size=1280x720:rate=15" \
        -vcodec libx264 -preset ultrafast -tune zerolatency -pix_fmt yuv420p \
        -f rtsp -rtsp_transport tcp "rtsp://127.0.0.1:8554/live/cam${i}_main" > /dev/null 2>&1 &
done

echo ""
echo "✅ RTSP Server is READY!"
echo "   Stream URL: rtsp://127.0.0.1:8554/live/cam1_sub"
echo "   Stream URL: rtsp://127.0.0.1:8554/live/cam2_sub"
echo "   (Press Ctrl+C to stop the server)"
echo ""

# Keep server alive
wait $SERVER_PID
