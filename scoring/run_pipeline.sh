#!/bin/bash
# Full scoring pipeline for workflow_simplicity, x_scale, x_sub
# Phase 0 and Phase 1 should already be complete before running this.

set -e
cd "$(dirname "$0")/.."

echo "=== Phase 2: Batch Scoring (API) ==="
python3 scoring/phase2_batch_scorer.py

echo ""
echo "=== Phase 3: Auditor ==="
python3 scoring/phase3_auditor.py

echo ""
echo "=== Phase 4: Reliability Verification ==="
python3 scoring/phase4_reliability.py

echo ""
echo "=== Phase 5: Write-back to Workbook ==="
python3 scoring/phase5_writeback.py

echo ""
echo "=== PIPELINE COMPLETE ==="
