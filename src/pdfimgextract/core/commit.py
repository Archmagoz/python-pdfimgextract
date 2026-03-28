import os

from pdfimgextract.models.datamodels import ExtractResult
from pdfimgextract.utils.filesystem import remove_file_safely


def _invalid_result(
    result: ExtractResult,
    *,
    error: str,
) -> tuple[ExtractResult, str | None]:
    """
    Build a standardized failed result, preserving original metadata.
    """
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
    """
    Build a standardized successful result after finalization.
    """
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
    Finalize an extraction result by validating and committing the temp file.

    Returns the normalized result and the final file path (if successful).
    """

    # Propagate early if worker already failed or was cancelled
    if not result.ok:
        return result, None

    # Ensure worker produced a temporary file
    if result.temp_path is None:
        return _invalid_result(
            result,
            error="Invalid worker result: missing temp_path",
        )

    # Extension is required to construct the final filename
    if not result.ext:
        remove_file_safely(result.temp_path)
        return _invalid_result(
            result,
            error="Invalid worker result: missing extension",
        )

    # Build destination path
    final_path = os.path.join(out_dir, f"{result.stem}.{result.ext}")

    try:
        # Atomic rename: guarantees visibility only after full write
        os.replace(result.temp_path, final_path)
    except OSError as e:
        # Cleanup temp file on failure
        remove_file_safely(result.temp_path)
        return _invalid_result(
            result,
            error=str(e),
        )

    # Return normalized success result
    success_result, _ = _success_result(result)

    return success_result, final_path
