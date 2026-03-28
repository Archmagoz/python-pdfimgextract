from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True, frozen=True)
class Args:
    """Configuration parameters for the extraction process."""

    pdf_path: str
    out_dir: str
    workers: int
    overwrite: bool
    dedup: str


@dataclass(slots=True, frozen=True)
class ExtractTask:
    """Represents a single image extraction task."""

    xref: int
    out_dir: str
    stem: str


@dataclass(slots=True, frozen=True)
class ExtractResult:
    """Result of an extraction attempt."""

    ok: bool
    cancelled: bool
    xref: int
    stem: str
    ext: str | None
    temp_path: str | None
    error: str | None


@dataclass(slots=True, frozen=True)
class ExtractionSummary:
    """Aggregated summary of extraction results."""

    success: int
    failed: int
    interrupted: bool


@dataclass(slots=True, frozen=True)
class PoolResult:
    """Container for all results returned by the worker pool."""

    results: list[ExtractResult]
    success_count: int
    failed_count: int
    interrupted: bool


class SharedEventProtocol(Protocol):
    """
    Minimal interface for a shared stop event.
    """

    def is_set(self) -> bool: ...
    def set(self) -> None: ...
