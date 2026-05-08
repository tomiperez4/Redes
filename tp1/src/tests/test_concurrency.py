import os
import threading
from conftest import (
    SERVER_STORAGE,
    CLIENT_STORAGE,
    BASE_FILE,
    stored_name,
    run_upload,
    run_download,
    md5,
    wait_for_file,
)


def test_concurrent_upload_and_download(server):
    tasks = [
        (run_upload, "sw"),
        (run_upload, "gbn"),
        (run_download, "sw"),
        (run_download, "gbn"),
    ]

    results = [None] * len(tasks)
    start = threading.Event()

    def run(idx, fn, protocol):
        start.wait()
        results[idx] = fn(protocol)

    threads = [
        threading.Thread(target=run, args=(i, fn, proto))
        for i, (fn, proto) in enumerate(tasks)
    ]
    for t in threads:
        t.start()
    start.set()
    for t in threads:
        t.join(timeout=120)

    for i, (fn, proto) in enumerate(tasks):
        assert (
            results[i] is not None
        ), f"{'Upload' if fn == run_upload else 'Download'} [{proto}] timeouted"
        assert results[i].returncode == 0, (
            f"{'Upload' if fn == run_upload else 'Download'} failed [{proto}]\n"
            f"stdout: {results[i].stdout}\n"
            f"stderr: {results[i].stderr}"
        )

    # Validate uploads
    original_client = os.path.join(CLIENT_STORAGE, BASE_FILE)
    for _, proto in tasks[:2]:
        stored = os.path.join(SERVER_STORAGE, stored_name(proto))
        assert wait_for_file(stored), f"File not found in server storage [{proto}]"
        assert md5(original_client) == md5(
            stored
        ), f"Corrupt content in upload [{proto}]"

    # Validate downloads
    original_server = os.path.join(SERVER_STORAGE, BASE_FILE)
    for _, proto in tasks[2:]:
        downloaded = os.path.join(CLIENT_STORAGE, stored_name(proto))
        assert wait_for_file(downloaded), f"File not found in client storage [{proto}]"
        assert md5(original_server) == md5(
            downloaded
        ), f"Corrupt content in download [{proto}]"
