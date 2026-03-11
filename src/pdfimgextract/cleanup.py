import os

from contextlib import suppress


def remove_file_safely(path: str | None) -> None:
    if not path:
        return

    with suppress(OSError):
        os.remove(path)


def cleanup_stale_temp_files(out_dir: str) -> None:
    if not os.path.isdir(out_dir):
        return

    for name in os.listdir(out_dir):
        if name.startswith(".pdfimgextract-tmp-") and name.endswith(".part"):
            remove_file_safely(os.path.join(out_dir, name))
