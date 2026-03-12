from pdfimgextract import worker
from pdfimgextract.datamodels import ExtractTask


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
