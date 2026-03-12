from unittest.mock import Mock

from pdfimgextract.extract import (
    handle_interrupt,
    run_pool,
    extract_images_parallel,
)

from pdfimgextract.worker import ExtractResult
from pdfimgextract.exit_codes import EXIT_SUCCESS, EXIT_FAILURE


class DummyProgress:
    def __init__(self):
        self.updated = 0
        self.colour = None
        self.desc = None

    def update(self, n):
        self.updated += n

    def set_description(self, text):
        self.desc = text

    def refresh(self):
        pass


class DummyEvent:
    def __init__(self, state=False):
        self.state = state

    def is_set(self):
        return self.state

    def set(self):
        self.state = True


class DummyPool:
    def __init__(self, results):
        self.results = results
        self.closed = False
        self.terminated = False

    def imap_unordered(self, fn, tasks, chunksize=1):
        for r in self.results:
            yield r

    def close(self):
        self.closed = True

    def join(self):
        pass

    def terminate(self):
        self.terminated = True


def make_raw(ok=True):
    return ExtractResult(
        ok=ok,
        cancelled=False,
        xref=1,
        stem="img",
        ext="png",
        temp_path=None,
        error=None,
    )


def test_handle_interrupt():
    pool = Mock()
    progress = DummyProgress()
    stop = DummyEvent()

    handle_interrupt(pool, progress, stop)

    assert stop.is_set()
    pool.terminate.assert_called()
    pool.join.assert_called()
    assert progress.desc == "Cancelled (CTRL-C)"


def test_run_pool_normal(monkeypatch):
    raw = make_raw()

    pool = DummyPool([raw])
    progress = DummyProgress()
    stop = DummyEvent()

    monkeypatch.setattr("pdfimgextract.extract.Pool", lambda **k: pool)

    monkeypatch.setattr(
        "pdfimgextract.extract.finalize_result",
        lambda r, out_dir: (r, None),
    )

    results, failed, success, interrupted = run_pool(
        tasks=[1],
        workers=1,
        pdf_path="x.pdf",
        stop_event=stop,
        progress=progress,
        out_dir="out",
    )

    assert success == 1
    assert len(results) == 1
    assert not failed
    assert not interrupted


def test_run_pool_cancelled(monkeypatch):
    raw = ExtractResult(
        ok=True,
        cancelled=False,
        xref=1,
        stem="img",
        ext="png",
        temp_path="tmpfile",
        error=None,
    )

    pool = DummyPool([raw])
    progress = DummyProgress()
    stop = DummyEvent(True)

    monkeypatch.setattr("pdfimgextract.extract.Pool", lambda **k: pool)
    monkeypatch.setattr(
        "pdfimgextract.extract.remove_file_safely",
        lambda x: None,
    )

    results, failed, success, interrupted = run_pool(
        tasks=[1],
        workers=1,
        pdf_path="x.pdf",
        stop_event=stop,
        progress=progress,
        out_dir="out",
    )

    assert success == 0
    assert results[0].cancelled


def test_run_pool_keyboard_interrupt(monkeypatch):
    progress = DummyProgress()
    stop = DummyEvent()

    class KIpool(DummyPool):
        def imap_unordered(self, *a, **k):
            raise KeyboardInterrupt

    pool = KIpool([])

    monkeypatch.setattr("pdfimgextract.extract.Pool", lambda **k: pool)

    results, failed, success, interrupted = run_pool(
        tasks=[1],
        workers=1,
        pdf_path="x.pdf",
        stop_event=stop,
        progress=progress,
        out_dir="out",
    )

    assert interrupted


def test_extract_no_images(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "pdfimgextract.extract.build_tasks",
        lambda *a: [],
    )

    code = extract_images_parallel("x.pdf", str(tmp_path), 1)

    assert code == EXIT_SUCCESS


def test_extract_normal(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "pdfimgextract.extract.build_tasks",
        lambda *a: [1],
    )

    monkeypatch.setattr(
        "pdfimgextract.extract.create_progress_bar",
        lambda total: DummyProgress(),
    )

    monkeypatch.setattr(
        "pdfimgextract.extract.run_pool",
        lambda *a, **k: ([], [], 0, False),
    )

    monkeypatch.setattr(
        "pdfimgextract.extract.finish_progress_bar",
        lambda *a: None,
    )

    monkeypatch.setattr(
        "pdfimgextract.extract.print_summary",
        lambda *a: 0,
    )

    code = extract_images_parallel("x.pdf", str(tmp_path), 1)

    assert code == 0


def test_extract_fatal_error(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "pdfimgextract.extract.build_tasks",
        lambda *a: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    code = extract_images_parallel("x.pdf", str(tmp_path), 1)

    assert code == EXIT_FAILURE
