import hashlib
import os
import subprocess
import time

import pytest

# ─────────────────────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────────────────────

TESTS_DIR      = os.path.dirname(os.path.abspath(__file__))
SRC_DIR        = os.path.dirname(TESTS_DIR)
SERVER_STORAGE = os.path.join(TESTS_DIR, "server_storage")
CLIENT_STORAGE = os.path.join(TESTS_DIR, "client_storage")

HOST      = "127.0.0.1"
PORT      = 9090
BASE_FILE = "test_5mb.jpg"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def wait_for_file(path: str, timeout: float = 5.0, interval: float = 0.1):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(path):
            return True
        time.sleep(interval)
    return False

def md5(path: str):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def stored_name(protocol: str):
    return f"test_5mb_{protocol}.jpg"


def run_upload(protocol: str):
    return subprocess.run(
        [
            "python3", "upload.py",
            "-H", HOST,
            "-p", str(PORT),
            "-s", os.path.join(CLIENT_STORAGE, BASE_FILE),
            "-n", stored_name(protocol),
            "-r", protocol,
            "-q",
        ],
        cwd=SRC_DIR,
        timeout=120,
        capture_output=True,
        text=True,
    )


def run_download(protocol: str):
    return subprocess.run(
        [
            "python3", "download.py",
            "-H", HOST,
            "-p", str(PORT),
            "-d", os.path.join(CLIENT_STORAGE, stored_name(protocol)),
            "-n", BASE_FILE,
            "-r", protocol,
            "-q",
        ],
        cwd=SRC_DIR,
        timeout=120,
        capture_output=True,
        text=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def check_test_data():
    for path in [
        os.path.join(SERVER_STORAGE, BASE_FILE),
        os.path.join(CLIENT_STORAGE, BASE_FILE),
    ]:
        assert os.path.exists(path), (
            f"Base file not found: {path}\n"
            f"Put {BASE_FILE} in the correct directory."
        )


@pytest.fixture(scope="session")
def server(check_test_data):
    proc = subprocess.Popen(
        [
            "python3", "start_server.py",
            "-H", HOST,
            "-p", str(PORT),
            "-s", SERVER_STORAGE,
            "-q",
        ],
        cwd=SRC_DIR,
    )
    time.sleep(0.8)
    assert proc.poll() is None, "Failed to start server"
    yield proc
    proc.terminate()
    proc.wait(timeout=5)


@pytest.fixture(autouse=True)
def cleanup_generated_files():
    yield
    for storage in [SERVER_STORAGE, CLIENT_STORAGE]:
        for protocol in ["sw", "gbn"]:
            path = os.path.join(storage, stored_name(protocol))
            if os.path.exists(path):
                os.remove(path)
