#!/bin/bash
# run_tests.sh
# Uso: bash tests/run_tests.sh [upload|download|concurrency|all]
# Run from src/

set -e

HOST="127.0.0.1"
PORT=9090
TESTS_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="$(dirname "$TESTS_DIR")"
SERVER_STORAGE="$TESTS_DIR/server_storage"
CLIENT_STORAGE="$TESTS_DIR/client_storage"
BASE_FILE="test_5mb.jpg"
SERVER_PID=""
SUITE="${1:-all}"

# ─────────────────────────────────────────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────────────────────────────────────────

cleanup() {
    echo ""
    if [ -n "$SERVER_PID" ]; then
        echo "[*] Deteniendo servidor (PID $SERVER_PID)..."
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

# ─────────────────────────────────────────────────────────────────────────────
# Verify base files
# ─────────────────────────────────────────────────────────────────────────────

echo "[*] Verifying base files..."
for storage in "$SERVER_STORAGE" "$CLIENT_STORAGE"; do
    file="$storage/$BASE_FILE"
    if [ ! -f "$file" ]; then
        echo "[!] Base file not found: $file"
        echo "    Put $BASE_FILE in $storage"
        exit 1
    fi
    echo "    OK: $file ($(du -h "$file" | cut -f1))"
done

# ─────────────────────────────────────────────────────────────────────────────
# Run tests
# ─────────────────────────────────────────────────────────────────────────────

case "$SUITE" in
    upload)
        pytest "$TESTS_DIR/test_upload.py" -v
        ;;
    download)
        pytest "$TESTS_DIR/test_download.py" -v
        ;;
    concurrency)
        pytest "$TESTS_DIR/test_concurrency.py" -v
        ;;
    all)
        pytest "$TESTS_DIR/test_upload.py" \
               "$TESTS_DIR/test_download.py" \
               "$TESTS_DIR/test_concurrency.py" -v
        ;;
    *)
        echo "[!] Unknwown suite: $SUITE"
        echo "    Uso: bash tests/run_tests.sh [upload|download|concurrency|all]"
        exit 1
        ;;
esac