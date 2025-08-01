#!/usr/bin/env bash

# Production Migration Script with Enhanced Validation
# This script demonstrates a production-ready migration workflow

set -e  # Exit on error

# Configuration
COGNOS_URL="${COGNOS_URL:-http://20.244.32.126:9300/api/v1}"
SESSION_KEY="${1:-}"  # Pass session key as first argument
MODULE_ID="${2:-}"    # Pass module ID as second argument
OUTPUT_BASE="${OUTPUT_BASE:-./output/production}"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Validate inputs
if [ -z "$SESSION_KEY" ] || [ -z "$MODULE_ID" ]; then
    print_error "Usage: $0 <session_key> <module_id>"
    exit 1
fi

# Create output directory
OUTPUT_PATH="$OUTPUT_BASE/${MODULE_ID}_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTPUT_PATH"

print_status "Starting enhanced migration for module: $MODULE_ID"
print_status "Output directory: $OUTPUT_PATH"

# Step 1: Test connection
print_status "Testing Cognos connection..."
if ./bimigrator-enhanced test-connection \
    --cognos-url "$COGNOS_URL" \
    --session-key "$SESSION_KEY" \
    --enable-validation; then
    print_status "✓ Connection test passed"
else
    print_error "Connection test failed"
    exit 1
fi

# Step 2: Validate module first (dry run)
print_status "Validating module structure..."
if ./bimigrator-enhanced validate-module \
    --module-id "$MODULE_ID" \
    --cognos-url "$COGNOS_URL" \
    --session-key "$SESSION_KEY" \
    --output-report "$OUTPUT_PATH/validation_report.json"; then
    print_status "✓ Module validation passed"
else
    print_warning "Module validation reported issues - check validation_report.json"
fi

# Step 3: Perform migration with enhanced validation
print_status "Starting module migration with enhanced validation..."

# Create error log file
ERROR_LOG="$OUTPUT_PATH/migration_errors.log"
touch "$ERROR_LOG"

# Run migration
if ./bimigrator-enhanced migrate-module \
    --module-id "$MODULE_ID" \
    --output-path "$OUTPUT_PATH" \
    --cognos-url "$COGNOS_URL" \
    --session-key "$SESSION_KEY" \
    --enable-enhanced-validation \
    --validation-config '{"validation_strictness": "high", "enable_select_star_fallback": true, "fallback_threshold": 0.8}' \
    --include-performance-metrics \
    --error-log-path "$ERROR_LOG" \
    --verbose; then
    
    print_status "✓ Module migration completed successfully"
    
    # Step 4: Post-process with quality report
    print_status "Generating quality reports..."
    
    if ./bimigrator-enhanced post-process \
        --module-id "$MODULE_ID" \
        --output-path "$OUTPUT_PATH" \
        --cognos-url "$COGNOS_URL" \
        --session-key "$SESSION_KEY" \
        --generate-quality-report; then
        
        print_status "✓ Post-processing completed"
    else
        print_warning "Post-processing encountered issues"
    fi
    
else
    print_error "Migration failed - check error log: $ERROR_LOG"
    exit 1
fi

# Step 5: Generate summary report
print_status "Generating migration summary..."

cat > "$OUTPUT_PATH/migration_summary.txt" << EOF
Migration Summary
================
Date: $(date)
Module ID: $MODULE_ID
Output Path: $OUTPUT_PATH

Files Generated:
$(find "$OUTPUT_PATH" -type f -name "*.tmdl" -o -name "*.json" -o -name "*.html" | wc -l) files

Migration Reports:
- Validation Report: validation_report.json
- Error Log: migration_errors.log
- Quality Report: quality_report.html (if generated)

Next Steps:
1. Review the validation_report.json for any warnings
2. Check migration_errors.log for any errors
3. Review the quality_report.html for migration quality metrics
4. Test the generated Power BI files in Power BI Desktop
EOF

print_status "✓ Migration complete! Summary saved to: $OUTPUT_PATH/migration_summary.txt"

# Optional: Open output directory
if command -v open &> /dev/null; then
    open "$OUTPUT_PATH"
elif command -v xdg-open &> /dev/null; then
    xdg-open "$OUTPUT_PATH"
fi

exit 0