# BhoomiAI Phase 3 — Consistency & Human Review

## Purpose

Phase 3 turns extracted land-record fields into an explainable verification layer.
The system checks internal consistency, configured reference hierarchy consistency,
and routes uncertain values to a human reviewer.

## Verification boundary

BhoomiAI does **not** establish legal ownership or government authenticity.
A validation result means only that the extracted information passed or failed
the configured data-quality checks.

## Checks

- duplicate extracted values that agree or conflict
- survey / gat / hissa-style identifier consistency
- village, taluka and district reference consistency when reference data is configured
- positive/numeric area sanity
- mutation date versus registration date chronology
- existing field-level required-value and format rules

## Review workflow

1. AI produces a field value and confidence.
2. Validation produces an explainable rule result.
3. REVIEW/WARNING/FLAGGED values enter the human review queue.
4. Reviewer can open the document, accept, verify, flag, or edit the value.
5. An edit requires a reason.
6. The audit log preserves the original value, corrected value, action, reviewer and reason.

## Status precedence

`REVIEW > WARNING > PASS`

A later PASS result never downgrades an earlier REVIEW/WARNING signal for the same field.

## Next extension

The next data layer can compare related records (for example 7/12 and mutation records)
using a stable record/parcel key, while retaining the same evidence-linked review workflow.
