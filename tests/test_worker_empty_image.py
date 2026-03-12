from pdfimgextract import worker
from pdfimgextract.datamodels import ExtractTask


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
