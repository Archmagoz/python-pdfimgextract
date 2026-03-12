import sys
import pytest

from pdfimgextract.args import get_args
from pdfimgextract.exit_codes import EXIT_BY_INCORRECT_USAGE


def make_pdf(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    return pdf


def test_args_full_flags(monkeypatch, tmp_path):
    pdf = make_pdf(tmp_path)

    monkeypatch.setattr(
        sys,
        "argv",
        ["prog", "-i", str(pdf), "-o", "out", "-p", "4"],
    )

    args = get_args()

    assert args.input == str(pdf)
    assert args.output == "out"
    assert args.parallelism == 4


def test_args_positional(monkeypatch, tmp_path):
    pdf = make_pdf(tmp_path)

    monkeypatch.setattr(
        sys,
        "argv",
        ["prog", str(pdf), "out", "6"],
    )

    args = get_args()

    assert args.input == str(pdf)
    assert args.output == "out"
    assert args.parallelism == 6


def test_default_parallelism(monkeypatch, tmp_path):
    pdf = make_pdf(tmp_path)

    monkeypatch.setattr(
        sys,
        "argv",
        ["prog", str(pdf), "-o", "out"],
    )

    args = get_args()

    assert args.parallelism == 8


def test_missing_input(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog", "-o", "out"])

    with pytest.raises(SystemExit) as e:
        get_args()

    assert e.value.code == EXIT_BY_INCORRECT_USAGE


def test_missing_output(monkeypatch, tmp_path):
    pdf = make_pdf(tmp_path)

    monkeypatch.setattr(sys, "argv", ["prog", str(pdf)])

    with pytest.raises(SystemExit) as e:
        get_args()

    assert e.value.code == EXIT_BY_INCORRECT_USAGE


def test_invalid_input_file(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog", "missing.pdf", "-o", "out"])

    with pytest.raises(SystemExit) as e:
        get_args()

    assert e.value.code == EXIT_BY_INCORRECT_USAGE


def test_output_is_file(monkeypatch, tmp_path):
    pdf = make_pdf(tmp_path)
    out_file = tmp_path / "out"
    out_file.write_text("not a dir")

    monkeypatch.setattr(
        sys,
        "argv",
        ["prog", str(pdf), "-o", str(out_file)],
    )

    with pytest.raises(SystemExit) as e:
        get_args()

    assert e.value.code == EXIT_BY_INCORRECT_USAGE


def test_invalid_parallelism(monkeypatch, tmp_path):
    pdf = make_pdf(tmp_path)

    monkeypatch.setattr(
        sys,
        "argv",
        ["prog", str(pdf), "-o", "out", "-p", "0"],
    )

    with pytest.raises(SystemExit) as e:
        get_args()

    assert e.value.code == EXIT_BY_INCORRECT_USAGE
