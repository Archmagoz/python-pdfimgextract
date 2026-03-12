from pdfimgextract.progress_bar import create_progress_bar, finish_progress_bar


def test_create_progress_bar():
    total = 5

    progress = create_progress_bar(total)
    assert progress.total == total
    assert progress.desc == "Extracting images"
    assert progress.unit == " img"
    assert progress.n == 0


def test_progress_bar_update():
    total = 5
    progress = create_progress_bar(total)

    for i in range(total):
        progress.update(1)
        assert progress.n == i + 1

    finish_progress_bar(progress)
    assert progress.n == total
