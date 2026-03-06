#!/bin/bash
# Task Pipeline: O*NET extraction → LLM curation/scoring → workbook writeback
#
# Usage: bash scoring/task_pipeline/run.sh
# Requires: ANTHROPIC_API_KEY environment variable

set -e
cd "$(dirname "$0")/../.."

echo "============================================"
echo "  Task Pipeline — O*NET Hybrid Approach"
echo "============================================"
echo ""

# Check prerequisites
if [ ! -f "onet_data/db_29_1_text/Task Statements.txt" ]; then
    echo "ERROR: O*NET data not found. Run onet_extract.py first or download the database."
    exit 1
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "ERROR: ANTHROPIC_API_KEY not set."
    echo "  export ANTHROPIC_API_KEY=sk-ant-..."
    exit 1
fi

echo "=== Phase 0: O*NET Extraction ==="
python3 scoring/task_pipeline/onet_extract.py
echo ""

echo "=== Phase 1: LLM Curation & Autonomy Scoring ==="
echo "  (357 SOC entries, ~15 min with 6 workers)"
python3 scoring/task_pipeline/curate_and_score.py
echo ""

echo "=== Phase 2: Writeback & Bottleneck Flagging ==="
python3 scoring/task_pipeline/writeback.py
echo ""

echo "============================================"
echo "  PIPELINE COMPLETE"
echo "============================================"
echo ""
echo "Outputs:"
echo "  Workbook:    jobs-data-v3.xlsx (3 Tasks tab)"
echo "  Scores:      scoring/task_pipeline/scored_tasks.json"
echo "  Bottlenecks: scoring/task_pipeline/bottleneck_report.txt"
