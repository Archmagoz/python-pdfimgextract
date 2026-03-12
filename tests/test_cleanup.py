from pdfimgextract.cleanup import (
    remove_file_safely,
    cleanup_stale_temp_files,
)


def test_remove_file_safely_none():
    remove_file_safely(None)


def test_remove_file_safely_empty():
    remove_file_safely("")


def test_remove_existing_file(tmp_path):
    f = tmp_path / "file.txt"
    f.write_text("data")

    remove_file_safely(str(f))

    assert not f.exists()


def test_remove_missing_file():
    remove_file_safely("does_not_exist.txt")


def test_cleanup_dir_not_exists(tmp_path):
    cleanup_stale_temp_files(str(tmp_path / "missing"))


def test_cleanup_no_temp_files(tmp_path):
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b.jpg").write_text("b")

    cleanup_stale_temp_files(str(tmp_path))

    assert (tmp_path / "a.txt").exists()
    assert (tmp_path / "b.jpg").exists()


def test_cleanup_removes_temp_files(tmp_path):
    tmp1 = tmp_path / ".pdfimgextract-tmp-1.part"
    tmp2 = tmp_path / ".pdfimgextract-tmp-2.part"

    tmp1.write_text("x")
    tmp2.write_text("y")

    cleanup_stale_temp_files(str(tmp_path))

    assert not tmp1.exists()
    assert not tmp2.exists()


def test_cleanup_mixed_files(tmp_path):
    tmp = tmp_path / ".pdfimgextract-tmp-123.part"
    normal = tmp_path / "image.png"

    tmp.write_text("tmp")
    normal.write_text("img")

    cleanup_stale_temp_files(str(tmp_path))

    assert not tmp.exists()
    assert normal.exists()
