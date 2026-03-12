from pdfimgextract.commit import finalize_result
from pdfimgextract.datamodels import ExtractResult

from typing import Any


def make_result(**kwargs):
    base: dict[str, Any] = dict(
        ok=True,
        cancelled=False,
        xref=1,
        stem="img",
        ext="png",
        temp_path="tmpfile",
        error=None,
    )

    base.update(kwargs)
    return ExtractResult(**base)


def test_result_not_ok():
    r = make_result(ok=False)

    result, path = finalize_result(r, "out")

    assert result == r
    assert path is None


def test_missing_temp_path():
    r = make_result(temp_path=None)

    result, path = finalize_result(r, "out")

    assert not result.ok
    assert result.ok is False
    assert path is None


def test_missing_extension(monkeypatch):
    called = {}

    def fake_remove(path):
        called["path"] = path

    monkeypatch.setattr(
        "pdfimgextract.commit.remove_file_safely",
        fake_remove,
    )

    r = make_result(ext=None)

    result, path = finalize_result(r, "out")

    assert not result.ok
    assert result.ok is False
    assert called["path"] == "tmpfile"
    assert path is None


def test_replace_failure(monkeypatch):
    def fake_replace(a, b):
        raise OSError("disk error")

    monkeypatch.setattr("os.replace", fake_replace)

    removed = {}

    def fake_remove(path):
        removed["path"] = path

    monkeypatch.setattr(
        "pdfimgextract.commit.remove_file_safely",
        fake_remove,
    )

    r = make_result()

    result, path = finalize_result(r, "out")

    assert not result.ok
    assert result.ok is False
    assert removed["path"] == "tmpfile"
    assert path is None


def test_success(monkeypatch, tmp_path):
    replaced = {}

    def fake_replace(src, dst):
        replaced["src"] = src
        replaced["dst"] = dst

    monkeypatch.setattr("os.replace", fake_replace)

    monkeypatch.setattr(
        "pdfimgextract.commit.fix_ext",
        lambda x: "png",
    )

    r = make_result()

    result, path = finalize_result(r, str(tmp_path))

    assert result.ok
    assert path is not None
    assert path.endswith("img.png")

    assert replaced["src"] == "tmpfile"
