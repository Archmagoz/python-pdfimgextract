from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractTask:
    xref: int
    stem: str
    out_dir: str
    run_id: str


@dataclass(frozen=True)
class ExtractResult:
    ok: bool
    cancelled: bool
    xref: int
    stem: str
    ext: str | None
    temp_path: str | None
    error: str | None
