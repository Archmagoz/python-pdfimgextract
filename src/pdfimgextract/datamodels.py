from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Args:
    pdf_path: str
    out_dir: str
    workers: int
    overwrite: bool
    dedup: str


@dataclass(slots=True, frozen=True)
class ExtractTask:
    xref: int
    out_dir: str
    stem: str
    run_id: str


@dataclass(slots=True, frozen=True)
class ExtractResult:
    ok: bool
    cancelled: bool
    xref: int
    stem: str
    ext: str | None
    temp_path: str | None
    error: str | None


@dataclass(slots=True, frozen=True)
class ExtractionSummary:
    success: int
    failed: int
    interrupted: bool
