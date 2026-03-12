import pytest
from pdfimgextract.utils import fix_ext


@pytest.mark.parametrize(
    "input_ext, expected",
    [
        ("jpx", "jpg"),
        ("JPG", "jpg"),
        ("png", "png"),
        ("GIF", "gif"),
        ("tiff", "tiff"),
    ],
)
def test_fix_ext(input_ext, expected):
    assert fix_ext(input_ext) == expected
