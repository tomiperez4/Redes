import os
import pytest
from conftest import SERVER_STORAGE, CLIENT_STORAGE, BASE_FILE, stored_name, run_download, md5, wait_for_file


@pytest.mark.parametrize("protocol", ["sw", "gbn"])
def test_download(server, protocol):
    result = run_download(protocol)

    assert result.returncode == 0, (
        f"Download failed [{protocol}]\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )

    original   = os.path.join(SERVER_STORAGE, BASE_FILE)
    downloaded = os.path.join(CLIENT_STORAGE, stored_name(protocol))

    assert wait_for_file(downloaded), \
        f"File does not appear in client storage [{protocol}]"
    assert os.path.getsize(downloaded) == os.path.getsize(original), \
        f"Incorrect size [{protocol}]"
    assert md5(original) == md5(downloaded), \
        f"Corrupt content [{protocol}]"