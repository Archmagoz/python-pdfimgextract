import os

from dataclasses import replace

from pdfimgextract.models.types import ExtractResult
from pdfimgextract.utils.filesystem import remove_file_safely


def _invalid_result(result: ExtractResult, *, error: str) -> ExtractResult:
    """
    Build a standardized failed result, preserving original metadata.
    """
    return replace(result, ok=False, cancelled=False, temp_path=None, error=error)


def _success_result(result: ExtractResult) -> ExtractResult:
    """
    Build a standardized successful result after finalization.
    """
    return replace(result, ok=True, cancelled=False, temp_path=None, error=None)


def finalize_result(result: ExtractResult, out_dir: str) -> ExtractResult:
    """
    Finalize an extraction result by validating and committing the temp file.

    Returns the normalized result (if successful).
    """

    # Propagate early if worker already failed or was cancelled
    if not result.ok:
        return result

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
        return _invalid_result(result, error=str(e))

    # Return normalized success result
    return _success_result(result)
