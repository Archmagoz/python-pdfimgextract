from dataclasses import dataclass
from typing import List


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


@dataclass(slots=True, frozen=True)
class PoolResult:
    results: List[ExtractResult]
    success_count: int
    failed_count: int
    interrupted: bool
