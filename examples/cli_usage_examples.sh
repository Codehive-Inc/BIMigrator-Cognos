#!/usr/bin/env bash

# Enhanced BIMigrator-Cognos CLI Usage Examples
# This file contains example commands for using the enhanced CLI

# Set your Cognos credentials (replace with actual values)
COGNOS_URL="http://20.244.32.126:9300/api/v1"
SESSION_KEY="CAM AWkyOTE4..."  # Replace with your actual session key
MODULE_ID="i5F34A7A52E2645C0AB03C34BA50941D7"
REPORT_ID="iREPORT456"
OUTPUT_BASE="./output"

echo "=== Enhanced BIMigrator-Cognos CLI Usage Examples ==="
echo

# 1. Test Connection
echo "1. Test Connection with Validation Framework:"
echo "./bimigrator-enhanced test-connection \\"
echo "    --cognos-url \"$COGNOS_URL\" \\"
echo "    --session-key \"$SESSION_KEY\" \\"
echo "    --enable-validation"
echo

# 2. Basic Module Migration
echo "2. Basic Module Migration with Enhanced Validation:"
echo "./bimigrator-enhanced migrate-module \\"
echo "    --module-id \"$MODULE_ID\" \\"
echo "    --output-path \"$OUTPUT_BASE/module_basic\" \\"
echo "    --cognos-url \"$COGNOS_URL\" \\"
echo "    --session-key \"$SESSION_KEY\" \\"
echo "    --enable-enhanced-validation"
echo

# 3. Advanced Module Migration with All Features
echo "3. Advanced Module Migration with All Features:"
echo "./bimigrator-enhanced migrate-module \\"
echo "    --module-id \"$MODULE_ID\" \\"
echo "    --output-path \"$OUTPUT_BASE/module_advanced\" \\"
echo "    --cognos-url \"$COGNOS_URL\" \\"
echo "    --session-key \"$SESSION_KEY\" \\"
echo "    --enable-enhanced-validation \\"
echo "    --validation-config '{\"validation_strictness\": \"high\", \"enable_select_star_fallback\": true}' \\"
echo "    --enable-websocket \\"
echo "    --websocket-url \"ws://localhost:8765\" \\"
echo "    --include-performance-metrics \\"
echo "    --error-log-path \"./migration_errors.log\" \\"
echo "    --verbose"
echo

# 4. Report Migration
echo "4. Single Report Migration:"
echo "./bimigrator-enhanced migrate-report \\"
echo "    --report-id \"$REPORT_ID\" \\"
echo "    --output-path \"$OUTPUT_BASE/report\" \\"
echo "    --cognos-url \"$COGNOS_URL\" \\"
echo "    --session-key \"$SESSION_KEY\" \\"
echo "    --enable-enhanced-validation"
echo

# 5. Post-Processing with Quality Report
echo "5. Post-Process Module with Quality Report:"
echo "./bimigrator-enhanced post-process \\"
echo "    --module-id \"$MODULE_ID\" \\"
echo "    --output-path \"$OUTPUT_BASE/module_advanced\" \\"
echo "    --cognos-url \"$COGNOS_URL\" \\"
echo "    --session-key \"$SESSION_KEY\" \\"
echo "    --report-ids \"report1,report2,report3\" \\"
echo "    --generate-quality-report"
echo

# 6. Launch Dashboard
echo "6. Launch Quality Dashboard:"
echo "./bimigrator-enhanced dashboard \\"
echo "    --port 5000 \\"
echo "    --db-path \"./migration_metrics.db\""
echo

# 7. Batch Migration
echo "7. Batch Module Migration:"
echo "# First create a file with module IDs (one per line)"
echo "echo \"module1\" > modules.txt"
echo "echo \"module2\" >> modules.txt"
echo "echo \"module3\" >> modules.txt"
echo
echo "./bimigrator-enhanced batch-migrate \\"
echo "    --modules-file \"modules.txt\" \\"
echo "    --output-base-path \"$OUTPUT_BASE/batch\" \\"
echo "    --cognos-url \"$COGNOS_URL\" \\"
echo "    --session-key \"$SESSION_KEY\" \\"
echo "    --enable-enhanced-validation \\"
echo "    --parallel-workers 2 \\"
echo "    --continue-on-error"
echo

# 8. Validation Only (Dry Run)
echo "8. Validate Module Without Migration:"
echo "./bimigrator-enhanced validate-module \\"
echo "    --module-id \"$MODULE_ID\" \\"
echo "    --cognos-url \"$COGNOS_URL\" \\"
echo "    --session-key \"$SESSION_KEY\" \\"
echo "    --output-report \"./validation_report.json\""
echo

# 9. Using Configuration File
echo "9. Using Configuration File:"
echo "# First create a config file"
echo "cat > enhanced_config.json << EOF"
echo "{"
echo "    \"validation_config\": {"
echo "        \"validation_enabled\": true,"
echo "        \"validation_strictness\": \"high\","
echo "        \"enable_select_star_fallback\": true,"
echo "        \"fallback_threshold\": 0.8"
echo "    },"
echo "    \"websocket_config\": {"
echo "        \"enabled\": true,"
echo "        \"url\": \"ws://localhost:8765\""
echo "    },"
echo "    \"reporting_config\": {"
echo "        \"generate_html\": true,"
echo "        \"generate_comprehensive\": true"
echo "    }"
echo "}"
echo "EOF"
echo
echo "./bimigrator-enhanced migrate-module \\"
echo "    --config-file enhanced_config.json \\"
echo "    --module-id \"$MODULE_ID\" \\"
echo "    --output-path \"$OUTPUT_BASE/module_config\" \\"
echo "    --cognos-url \"$COGNOS_URL\" \\"
echo "    --session-key \"$SESSION_KEY\""
echo

# 10. Help Commands
echo "10. Help and Information Commands:"
echo "# General help"
echo "./bimigrator-enhanced --help"
echo
echo "# Command-specific help"
echo "./bimigrator-enhanced migrate-module --help"
echo
echo "# List available strategies"
echo "./bimigrator-enhanced list-strategies"
echo
echo "# Show configuration options"
echo "./bimigrator-enhanced show-validation-config"
echo

# 11. Environment Variable Setup
echo "11. Using Environment Variables:"
echo "# Set environment variables for configuration"
echo "export USE_ENHANCED_CONVERTER=true"
echo "export USE_ENHANCED_MQUERY_CONVERTER=true"
echo "export VALIDATION_STRICTNESS=high"
echo "export ENABLE_SELECT_STAR_FALLBACK=true"
echo
echo "# Then run without explicit validation config"
echo "./bimigrator-enhanced migrate-module \\"
echo "    --module-id \"$MODULE_ID\" \\"
echo "    --output-path \"$OUTPUT_BASE/module_env\" \\"
echo "    --cognos-url \"$COGNOS_URL\" \\"
echo "    --session-key \"$SESSION_KEY\""
echo

echo "=== End of Examples ===""