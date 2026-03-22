import os

from pdfimgextract.models.datamodels import ExtractResult
from pdfimgextract.utils.filesystem import remove_file_safely


def _invalid_result(
    result: ExtractResult,
    *,
    error: str,
) -> tuple[ExtractResult, str | None]:
    return (
        ExtractResult(
            ok=False,
            cancelled=False,
            xref=result.xref,
            stem=result.stem,
            ext=result.ext,
            temp_path=None,
            error=error,
        ),
        None,
    )


def _success_result(result: ExtractResult) -> tuple[ExtractResult, str | None]:
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
        None,
    )


def finalize_result(
    result: ExtractResult,
    out_dir: str,
) -> tuple[ExtractResult, str | None]:
    """
    Finalize an extraction result by committing the temporary file.
    """

    # If the worker already reported failure or cancellation, propagate it
    if not result.ok:
        return result, None

    # Validate worker output
    if result.temp_path is None:
        return _invalid_result(
            result,
            error="Invalid worker result: missing temp_path",
        )

    # Extension must exist to build the final filename
    if not result.ext:
        remove_file_safely(result.temp_path)
        return _invalid_result(
            result,
            error="Invalid worker result: missing extension",
        )

    # Build final output path
    final_path = os.path.join(out_dir, f"{result.stem}.{result.ext}")

    try:
        # Atomic rename ensures the file appears only when fully written
        os.replace(result.temp_path, final_path)
    except OSError as e:
        remove_file_safely(result.temp_path)
        return _invalid_result(
            result,
            error=str(e),
        )

    # Return a clean finalized result
    success_result, _ = _success_result(result)
    return success_result, final_path
