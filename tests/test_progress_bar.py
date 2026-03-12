from pdfimgextract.progress_bar import create_progress_bar


def test_progress_bar_creation():
    bar = create_progress_bar(10)

    assert bar.total == 10
