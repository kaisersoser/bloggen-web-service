#!/bin/bash
# Backend Log Monitor Script
# Provides real-time monitoring of backend.log with color-coded output

LOG_FILE="backend.log"

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=========================================="
echo "  Backend Log Monitor Started"
echo "  Log file: $LOG_FILE"
echo "  Press Ctrl+C to stop"
echo "=========================================="
echo ""

# Function to colorize output
colorize_line() {
    local line="$1"
    
    if echo "$line" | grep -qiE "error|failed|exception"; then
        echo -e "${RED}${line}${NC}"
    elif echo "$line" | grep -qiE "warning|warn"; then
        echo -e "${YELLOW}${line}${NC}"
    elif echo "$line" | grep -qE "✅|SUCCESS|Initialized|complete"; then
        echo -e "${GREEN}${line}${NC}"
    elif echo "$line" | grep -qE "INFO|Starting|Running"; then
        echo -e "${BLUE}${line}${NC}"
    else
        echo "$line"
    fi
}

# Show last 20 lines with colors
echo "Recent log entries:"
echo "------------------------------------------"
tail -20 "$LOG_FILE" | while IFS= read -r line; do
    colorize_line "$line"
done
echo "------------------------------------------"
echo ""
echo "Monitoring for new entries..."
echo ""

# Follow the log file with colors
tail -f "$LOG_FILE" | while IFS= read -r line; do
    colorize_line "$line"
done
