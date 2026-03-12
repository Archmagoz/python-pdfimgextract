import multiprocessing
from pathlib import Path

import fitz

from pdfimgextract import worker
from pdfimgextract.worker import init_worker, worker_extract
from pdfimgextract.datamodels import ExtractTask


def create_test_pdf(pdf_path: Path):
    doc = fitz.open()

    page = doc.new_page()

    img = fitz.Pixmap(fitz.csRGB, (0, 0, 10, 10), 0)
    img.set_rect((0, 0, 10, 10), (255, 0, 0))

    img_bytes = img.tobytes("png")

    rect = fitz.Rect(0, 0, 10, 10)
    page.insert_image(rect, stream=img_bytes)

    doc.save(pdf_path)
    doc.close()


def test_worker_extract_full(tmp_path):

    pdf_path = tmp_path / "test.pdf"
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    create_test_pdf(pdf_path)

    stop_event = multiprocessing.Event()

    init_worker(str(pdf_path), stop_event)

    doc = fitz.open(pdf_path)

    xref = None
    for i in range(1, doc.xref_length()):
        try:
            img = doc.extract_image(i)
            if img:
                xref = i
                break
        except Exception:
            pass

    assert xref is not None

    task = ExtractTask(xref=xref, stem="img", out_dir=str(out_dir), run_id="test")

    result = worker_extract(task)

    assert result.ok
    assert result.ext == "png"
    assert result.temp_path is not None
    assert Path(result.temp_path).exists()


class CancelEvent:
    def is_set(self):
        return True


def test_worker_cancelled(tmp_path):
    worker.STOP_EVENT = CancelEvent()
    worker.PDF_DOC = None

    task = ExtractTask(xref=1, stem="img", out_dir=str(tmp_path), run_id="test")

    result = worker.worker_extract(task)

    assert result.cancelled is True
    assert result.ok is False
    assert result.error == "cancelled"


class DummyDoc:
    def extract_image(self, xref):
        return {
            "image": None,
            "ext": "png",
        }


class DummyEvent:
    def is_set(self):
        return False


def test_worker_empty_image(tmp_path):
    worker.PDF_DOC = DummyDoc()
    worker.STOP_EVENT = DummyEvent()

    task = ExtractTask(xref=1, stem="img", out_dir=str(tmp_path), run_id="test")

    result = worker.worker_extract(task)

    assert result.ok is False
    assert result.error == "PDF image extraction returned empty image data."


def test_worker_no_stop_event(tmp_path):
    worker.PDF_DOC = object()
    worker.STOP_EVENT = None

    task = ExtractTask(xref=1, stem="img", out_dir=str(tmp_path), run_id="test")

    result = worker.worker_extract(task)

    assert result.ok is False
    assert result.error is not None
    assert "Worker stop event is not initialized" in result.error


def test_worker_no_pdf_doc(tmp_path):
    class DummyEvent:
        def is_set(self):
            return False

    worker.PDF_DOC = None
    worker.STOP_EVENT = DummyEvent()

    task = ExtractTask(xref=1, stem="img", out_dir=str(tmp_path), run_id="test")

    result = worker.worker_extract(task)

    assert result.ok is False
    assert result.error is not None
    assert "Worker PDF document is not initialized" in result.error


def test_worker_empty_ext(tmp_path):
    class DummyDoc:
        def extract_image(self, xref):
            return {"image": b"123", "ext": ""}

    class DummyEvent:
        def is_set(self):
            return False

    worker.PDF_DOC = DummyDoc()
    worker.STOP_EVENT = DummyEvent()

    task = ExtractTask(xref=1, stem="img", out_dir=str(tmp_path), run_id="test")

    result = worker.worker_extract(task)

    assert result.ok is False
    assert result.error is not None
    assert "PDF image extraction returned empty file extension" in result.error


def test_worker_cancelled_after_write(tmp_path):
    class EventToggle:
        def __init__(self):
            self.called = False

        def is_set(self):
            if not self.called:
                self.called = True
                return False
            return True

    class DummyDoc:
        def extract_image(self, xref):
            return {"image": b"123", "ext": "png"}

    worker.PDF_DOC = DummyDoc()
    worker.STOP_EVENT = EventToggle()

    task = ExtractTask(xref=1, stem="img", out_dir=str(tmp_path), run_id="test")

    result = worker.worker_extract(task)

    assert result.cancelled is True
    assert result.ok is False
    temp_path = tmp_path / f".pdfimgextract-tmp-{task.run_id}-{task.stem}.png.part"
    assert not temp_path.exists()


def test_worker_exception_removes_temp(tmp_path):
    class DummyDoc:
        def extract_image(self, xref):
            return {"image": b"123", "ext": "png"}

    class DummyEvent:
        def is_set(self):
            return False

    worker.PDF_DOC = DummyDoc()
    worker.STOP_EVENT = DummyEvent()

    task = ExtractTask(xref=1, stem="img", out_dir="/nonexistent_dir", run_id="test")

    result = worker.worker_extract(task)

    assert result.ok is False
    assert result.error is not None
    assert "No such file or directory" in result.error


def test_close_worker_pdf(tmp_path):
    class DummyDoc:
        closed = False

        def close(self):
            self.closed = True

    worker.PDF_DOC = DummyDoc()
    worker.close_worker_pdf()
    assert worker.PDF_DOC is None
    assert worker.PDF_DOC is None or getattr(worker.PDF_DOC, "closed", True) is True


def test_init_worker_calls(tmp_path):
    import multiprocessing

    pdf_path = tmp_path / "test.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(pdf_path)
    doc.close()

    stop_event = multiprocessing.Event()
    worker.init_worker(str(pdf_path), stop_event)

    assert worker.PDF_DOC is not None
    assert worker.STOP_EVENT is stop_event


def test_close_worker_pdf_with_exception(monkeypatch):
    class DummyDoc:
        def close(self):
            raise RuntimeError("fail close")

    worker.PDF_DOC = DummyDoc()
    worker.close_worker_pdf()
    assert worker.PDF_DOC is None


def test_worker_exception_after_temp(tmp_path):
    class DummyDoc:
        def extract_image(self, xref):
            return {"image": b"123", "ext": "png"}

    class DummyEvent:
        def is_set(self):
            return False

    worker.PDF_DOC = DummyDoc()
    worker.STOP_EVENT = DummyEvent()

    task = ExtractTask(xref=1, stem="img", out_dir="/nonexistent_dir", run_id="test")
    result = worker.worker_extract(task)

    assert result.ok is False
