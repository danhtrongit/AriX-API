#!/bin/bash
# Script to monitor ingestion progress

echo "=================================="
echo "📊 MONITORING INGESTION PROGRESS"
echo "=================================="

# Check if process is still running
if pgrep -f "ingest_all_symbols_fast.py" > /dev/null; then
    echo "✅ Process is RUNNING"
else
    echo "⚠️  Process is NOT running (completed or stopped)"
fi

echo ""
echo "📈 Latest progress:"
echo "----------------------------------"

# Show success/error counts
if [ -f ingest_progress.log ]; then
    echo "✅ Successful symbols:"
    grep "✅ Thành công:" ingest_progress.log | wc -l | xargs echo "   Count:"
    
    echo ""
    echo "❌ Failed symbols:"
    grep "❌ Lỗi khi xử lý" ingest_progress.log | wc -l | xargs echo "   Count:"
    
    echo ""
    echo "📊 Last 10 processed symbols:"
    grep -E "\[.*Processing" ingest_progress.log | tail -10
    
    echo ""
    echo "⏱️  Statistics (if available):"
    grep -A 5 "📊 THỐNG KÊ" ingest_progress.log | tail -6
else
    echo "⚠️  Log file not found: ingest_progress.log"
fi

echo ""
echo "=================================="
echo "💡 Commands:"
echo "  - Watch live: tail -f ingest_progress.log"
echo "  - Rerun monitor: bash monitor_progress.sh"
echo "  - Stop process: pkill -f ingest_all_symbols_fast.py"
echo "=================================="

