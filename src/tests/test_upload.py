import os
import pytest
from conftest import (
    SERVER_STORAGE,
    CLIENT_STORAGE,
    BASE_FILE,
    stored_name,
    run_upload,
    md5,
    wait_for_file,
)


@pytest.mark.parametrize("protocol", ["sw", "gbn"])
def test_upload(server, protocol):
    result = run_upload(protocol)

    assert result.returncode == 0, (
        f"Upload failed [{protocol}]\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )

    original = os.path.join(CLIENT_STORAGE, BASE_FILE)
    stored = os.path.join(SERVER_STORAGE, stored_name(protocol))

    assert wait_for_file(stored), f"File does not appear in server storage [{protocol}]"
    assert os.path.getsize(stored) == os.path.getsize(
        original
    ), f"Incorrect size [{protocol}]"
    assert md5(original) == md5(stored), f"Corrupt content [{protocol}]"
