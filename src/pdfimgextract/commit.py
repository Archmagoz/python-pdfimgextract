import os

from pdfimgextract.datamodels import ExtractResult
from pdfimgextract.filesystem import remove_file_safely


def finalize_result(
    result: ExtractResult,
    out_dir: str,
) -> tuple[ExtractResult, str | None]:
    """
    Finalize an extraction result by committing the temporary file.

    If the worker successfully extracted an image, this function moves the
    temporary file to its final destination using an atomic rename. If the
    result is invalid or the rename fails, the temporary file is removed and
    a failure result is returned.

    Args:
        result (ExtractResult): Result produced by the worker process.
        out_dir (str): Directory where the final image file should be placed.

    Returns:
        tuple[ExtractResult, str | None]:
            - Updated result object reflecting the final status.
            - Path to the finalized file if successful, otherwise None.
    """

    # If the worker already reported failure or cancellation, propagate it
    if not result.ok:
        return result, None

    # Validate worker output
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

    # Extension must exist to build the final filename
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

    # Build final output path
    final_path = os.path.join(out_dir, f"{result.stem}.{result.ext}")

    try:
        # Atomic rename ensures the file appears only when fully written
        os.replace(result.temp_path, final_path)
    except OSError as e:
        # Cleanup temporary file if the rename fails
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

    # Return a clean finalized result
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
