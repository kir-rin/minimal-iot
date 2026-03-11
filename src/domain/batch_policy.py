from __future__ import annotations

from collections.abc import Sequence

from src.domain.types import BatchDecision, IngestMode, RecordValidationResult, ValidationError


def resolve_ingest_mode(value: str | None) -> tuple[IngestMode | None, ValidationError | None]:
    """Resolve and validate the ingest mode parameter.

    Args:
        value: The ingest mode string ('atomic', 'partial') or None.

    Returns:
        tuple: (IngestMode or None, ValidationError or None).
            Returns ATOMIC as default when value is None.
    """
    if value is None:
        return IngestMode.ATOMIC, None

    try:
        return IngestMode(value), None
    except ValueError:
        return None, ValidationError(
            field="ingest_mode",
            reason="Unsupported ingest mode",
            code="INVALID_INGEST_MODE",
        )


def summarize_atomic_result(results: Sequence[RecordValidationResult]) -> BatchDecision:
    """Summarize validation results for atomic batch policy.

    All records must be valid. If any record fails, entire batch is rejected.

    Args:
        results: Sequence of validation results for each record.

    Returns:
        BatchDecision: Decision with success=False if any record failed.
    """
    if not results:
        return build_noop_batch_decision(IngestMode.ATOMIC)

    errors = _collect_indexed_errors(results)
    if errors:
        return BatchDecision(
            success=False,
            ingest_mode=IngestMode.ATOMIC,
            accepted_count=0,
            rejected_count=len(results),
            errors=errors,
            accepted_records=[],
        )

    accepted_records = [result.reading for result in results if result.reading is not None]
    return BatchDecision(
        success=True,
        ingest_mode=IngestMode.ATOMIC,
        accepted_count=len(accepted_records),
        rejected_count=0,
        errors=[],
        accepted_records=accepted_records,
    )


def summarize_partial_result(results: Sequence[RecordValidationResult]) -> BatchDecision:
    """Summarize validation results for partial batch policy.

    Valid records are accepted even if some fail. Success is True if at least
    one record is accepted.

    Args:
        results: Sequence of validation results for each record.

    Returns:
        BatchDecision: Decision with accepted records and errors for rejected ones.
    """
    if not results:
        return build_noop_batch_decision(IngestMode.PARTIAL)

    accepted_records = [result.reading for result in results if result.reading is not None]
    errors = _collect_indexed_errors(results)
    accepted_count = len(accepted_records)

    return BatchDecision(
        success=accepted_count >= 1,
        ingest_mode=IngestMode.PARTIAL,
        accepted_count=accepted_count,
        rejected_count=len(errors),
        errors=errors,
        accepted_records=accepted_records,
    )


def build_noop_batch_decision(ingest_mode: IngestMode) -> BatchDecision:
    """Create a no-op batch decision for empty payloads.

    Args:
        ingest_mode: The ingest mode (ATOMIC or PARTIAL).

    Returns:
        BatchDecision: Decision indicating successful no-op.
    """
    return BatchDecision(
        success=True,
        ingest_mode=ingest_mode,
        accepted_count=0,
        rejected_count=0,
        errors=[],
        accepted_records=[],
    )


def _collect_indexed_errors(results: Sequence[RecordValidationResult]) -> list[ValidationError]:
    errors: list[ValidationError] = []

    for index, result in enumerate(results):
        if result.error is None:
            continue

        error = result.error
        errors.append(
            ValidationError(
                field=error.field,
                reason=error.reason,
                index=index,
                code=error.code,
            )
        )

    return errors
