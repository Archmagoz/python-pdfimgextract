from unittest.mock import patch
from pdfimgextract.build_tasks import build_tasks
from pdfimgextract.datamodels import ExtractTask


class DummyImage(tuple):
    def __new__(cls, xref):
        return tuple.__new__(cls, (xref,))


class DummyPage:
    def __init__(self, images):
        self._images = images

    def get_images(self, full=True):
        return self._images


class DummyPDF:
    def __init__(self, pages):
        self.pages = pages

    def __enter__(self):
        return self.pages

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def __iter__(self):
        return iter(self.pages)


@patch("pdfimgextract.build_tasks.fitz.open")
def test_build_tasks_with_images(mock_open):
    page1 = DummyPage([DummyImage(1), DummyImage(2)])
    page2 = DummyPage([DummyImage(2), DummyImage(3)])
    mock_open.return_value = DummyPDF([page1, page2])

    out_dir = "out"
    run_id = "123abc"

    tasks = build_tasks("dummy.pdf", out_dir, run_id)

    xrefs = [t.xref for t in tasks]
    assert xrefs == [1, 2, 3]

    stems = [t.stem for t in tasks]
    assert stems == ["1", "2", "3"]

    for t in tasks:
        assert t.out_dir == out_dir
        assert t.run_id == run_id
        assert isinstance(t, ExtractTask)


@patch("pdfimgextract.build_tasks.fitz.open")
def test_build_tasks_no_images(mock_open):
    page = DummyPage([])
    mock_open.return_value = DummyPDF([page])

    tasks = build_tasks("dummy.pdf", "out", "runid")

    assert tasks == []


@patch("pdfimgextract.build_tasks.fitz.open")
def test_build_tasks_zfill(mock_open):
    images = [DummyImage(i) for i in range(1, 13)]
    page = DummyPage(images)
    mock_open.return_value = DummyPDF([page])

    tasks = build_tasks("dummy.pdf", "out", "rid")

    stems = [t.stem for t in tasks]
    assert stems[0] == "01"
    assert stems[-1] == "12"
    assert all(len(s) == 2 for s in stems)
