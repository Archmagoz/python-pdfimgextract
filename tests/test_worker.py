import multiprocessing
from pathlib import Path

import fitz

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
