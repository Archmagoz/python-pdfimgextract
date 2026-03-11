import os

from .datamodels import ExtractResult
from .cleanup import remove_file_safely
from .utils import fix_ext


def finalize_result(
    result: ExtractResult,
    out_dir: str,
) -> tuple[ExtractResult, str | None]:
    if not result.ok:
        return result, None

    if result.temp_path is None:
        return (
            ExtractResult(
                ok=False,
                cancelled=False,
                xref=result.xref,
                stem=result.stem,
                ext=result.ext,
                temp_path=None,
                error="Invalid worker result: missing temp_path",
            ),
            None,
        )

    if not result.ext:
        remove_file_safely(result.temp_path)
        return (
            ExtractResult(
                ok=False,
                cancelled=False,
                xref=result.xref,
                stem=result.stem,
                ext=None,
                temp_path=None,
                error="Invalid worker result: missing extension",
            ),
            None,
        )

    final_path = os.path.join(out_dir, f"{result.stem}.{fix_ext(result.ext)}")

    try:
        os.replace(result.temp_path, final_path)
    except OSError as e:
        remove_file_safely(result.temp_path)
        return (
            ExtractResult(
                ok=False,
                cancelled=False,
                xref=result.xref,
                stem=result.stem,
                ext=result.ext,
                temp_path=None,
                error=str(e),
            ),
            None,
        )

    return (
        ExtractResult(
            ok=True,
            cancelled=False,
            xref=result.xref,
            stem=result.stem,
            ext=result.ext,
            temp_path=None,
            error=None,
        ),
        final_path,
    )
