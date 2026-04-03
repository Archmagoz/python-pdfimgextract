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

    # Filename is required to build final path
    if not result.filename:
        remove_file_safely(result.temp_path)
        return _invalid_result(
            result,
            error="Invalid worker result: missing filename",
        )

    # Ensure filename does not contain directories (safety)
    filename: str = os.path.basename(result.filename)
    final_path: str = os.path.join(out_dir, filename)

    try:
        # Atomic move: only visible when fully written
        os.replace(result.temp_path, final_path)
    except OSError as e:
        # Cleanup temp file on failure
        remove_file_safely(result.temp_path)
        return _invalid_result(result, error=str(e))

    return _success_result(result)
