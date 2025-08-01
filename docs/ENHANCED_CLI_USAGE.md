# Enhanced BIMigrator-Cognos CLI Usage Guide

This guide explains how to use the enhanced command-line interface (CLI) for BIMigrator-Cognos with the validation framework.

## Table of Contents
- [Installation](#installation)
- [Basic Usage](#basic-usage)
- [Commands](#commands)
- [Configuration](#configuration)
- [Examples](#examples)
- [Advanced Features](#advanced-features)

## Installation

The enhanced CLI is included in the BIMigrator-Cognos repository. No additional installation is required.

```bash
# Make the CLI executable
chmod +x bimigrator-enhanced

# Verify installation
./bimigrator-enhanced --help
```

## Basic Usage

### Command Structure
```bash
./bimigrator-enhanced <command> [options]
```

### Quick Start
```bash
# Test connection
./bimigrator-enhanced test-connection \
    --cognos-url "http://20.244.32.126:9300/api/v1" \
    --session-key "YOUR_SESSION_KEY" \
    --enable-validation

# Migrate a module
./bimigrator-enhanced migrate-module \
    --module-id "MODULE_ID" \
    --output-path "./output" \
    --cognos-url "http://20.244.32.126:9300/api/v1" \
    --session-key "YOUR_SESSION_KEY" \
    --enable-enhanced-validation
```

## Commands

### test-connection
Test Cognos connection and validation framework availability.

```bash
./bimigrator-enhanced test-connection \
    --cognos-url <url> \
    --session-key <key> \
    [--enable-validation]
```

### migrate-module
Migrate a Cognos module with optional enhanced validation.

```bash
./bimigrator-enhanced migrate-module \
    --module-id <id> \
    --output-path <path> \
    --cognos-url <url> \
    --session-key <key> \
    [--folder-id <id>] \
    [--enable-enhanced-validation] \
    [--validation-config '<json>'] \
    [--enable-websocket] \
    [--websocket-url <ws://url>] \
    [--include-performance-metrics] \
    [--error-log-path <path>] \
    [--dry-run]
```

### migrate-report
Migrate a single Cognos report.

```bash
./bimigrator-enhanced migrate-report \
    --report-id <id> \
    --output-path <path> \
    --cognos-url <url> \
    --session-key <key> \
    [--enable-enhanced-validation] \
    [--validation-config '<json>']
```

### post-process
Post-process a migrated module with quality reporting.

```bash
./bimigrator-enhanced post-process \
    --module-id <id> \
    --output-path <path> \
    --cognos-url <url> \
    --session-key <key> \
    [--report-ids <id1,id2,id3>] \
    [--generate-quality-report]
```

### dashboard
Launch the migration quality dashboard.

```bash
./bimigrator-enhanced dashboard \
    [--port <port>] \
    [--db-path <path>] \
    [--host <host>]
```

### batch-migrate
Migrate multiple modules in batch.

```bash
./bimigrator-enhanced batch-migrate \
    --modules-file <file> \
    --output-base-path <path> \
    --cognos-url <url> \
    --session-key <key> \
    [--enable-enhanced-validation] \
    [--parallel-workers <n>] \
    [--continue-on-error]
```

### validate-module
Validate a module without performing migration.

```bash
./bimigrator-enhanced validate-module \
    --module-id <id> \
    --cognos-url <url> \
    --session-key <key> \
    [--output-report <path>]
```

### list-strategies
List available validation strategies.

```bash
./bimigrator-enhanced list-strategies
```

### show-validation-config
Show validation configuration options.

```bash
./bimigrator-enhanced show-validation-config
```

## Configuration

### Configuration File
Create a JSON configuration file for reusable settings:

```json
{
    "validation_config": {
        "validation_enabled": true,
        "validation_strictness": "high",
        "fallback_enabled": true,
        "enable_select_star_fallback": true,
        "fallback_threshold": 0.8
    },
    "websocket_config": {
        "enabled": true,
        "url": "ws://localhost:8765"
    },
    "reporting_config": {
        "generate_html": true,
        "generate_json": true,
        "generate_comprehensive": true
    }
}
```

Use the configuration file:
```bash
./bimigrator-enhanced migrate-module \
    --config-file config.json \
    --module-id "MODULE_ID" \
    --output-path "./output" \
    --cognos-url "http://server:9300/api/v1" \
    --session-key "SESSION_KEY"
```

### Environment Variables
Set environment variables for default configuration:

```bash
export USE_ENHANCED_CONVERTER=true
export USE_ENHANCED_MQUERY_CONVERTER=true
export VALIDATION_STRICTNESS=high
export ENABLE_SELECT_STAR_FALLBACK=true
export DAX_API_URL=http://localhost:8080
```

### Validation Configuration Options

| Option | Values | Description |
|--------|--------|-------------|
| validation_strictness | low, medium, high | Level of validation strictness |
| enable_select_star_fallback | true, false | Enable SELECT * fallback for M-Query |
| fallback_threshold | 0.0 - 1.0 | Threshold for triggering fallback |
| max_fallback_attempts | integer | Maximum fallback attempts |

## Examples

### 1. Basic Module Migration
```bash
./bimigrator-enhanced migrate-module \
    --module-id "i5F34A7A52E2645C0AB03C34BA50941D7" \
    --output-path "./output/my_module" \
    --cognos-url "http://20.244.32.126:9300/api/v1" \
    --session-key "CAM AWkyOTE4..." \
    --enable-enhanced-validation
```

### 2. Production Migration with All Features
```bash
./bimigrator-enhanced migrate-module \
    --module-id "i5F34A7A52E2645C0AB03C34BA50941D7" \
    --output-path "./output/production" \
    --cognos-url "http://20.244.32.126:9300/api/v1" \
    --session-key "CAM AWkyOTE4..." \
    --enable-enhanced-validation \
    --validation-config '{"validation_strictness": "high", "enable_select_star_fallback": true}' \
    --enable-websocket \
    --websocket-url "ws://localhost:8765" \
    --include-performance-metrics \
    --error-log-path "./errors.log" \
    --verbose
```

### 3. Batch Migration Script
```bash
# Create modules list
cat > modules.txt << EOF
module1_id
module2_id
module3_id
EOF

# Run batch migration
./bimigrator-enhanced batch-migrate \
    --modules-file modules.txt \
    --output-base-path "./output/batch" \
    --cognos-url "http://20.244.32.126:9300/api/v1" \
    --session-key "CAM AWkyOTE4..." \
    --enable-enhanced-validation \
    --parallel-workers 2 \
    --continue-on-error
```

### 4. Validation Only (Dry Run)
```bash
./bimigrator-enhanced validate-module \
    --module-id "i5F34A7A52E2645C0AB03C34BA50941D7" \
    --cognos-url "http://20.244.32.126:9300/api/v1" \
    --session-key "CAM AWkyOTE4..." \
    --output-report "./validation_report.json"
```

## Advanced Features

### WebSocket Progress Tracking
Enable real-time progress tracking:

```bash
# Start a WebSocket server (in another terminal)
python -m websockets ws://localhost:8765

# Run migration with WebSocket
./bimigrator-enhanced migrate-module \
    --module-id "MODULE_ID" \
    --output-path "./output" \
    --cognos-url "http://server:9300/api/v1" \
    --session-key "SESSION_KEY" \
    --enable-websocket \
    --websocket-url "ws://localhost:8765"
```

### Quality Dashboard
Monitor migration quality metrics:

```bash
# Launch dashboard
./bimigrator-enhanced dashboard --port 5000

# Access dashboard in browser
open http://localhost:5000
```

### Production Workflow Script
Use the provided production script for a complete workflow:

```bash
./examples/production_migration.sh "SESSION_KEY" "MODULE_ID"
```

This script will:
1. Test connection
2. Validate module structure
3. Perform migration with enhanced validation
4. Generate quality reports
5. Create a summary report

### Docker Usage
Run in a Docker container:

```bash
docker run -v $(pwd)/output:/app/output \
    -e USE_ENHANCED_CONVERTER=true \
    -e VALIDATION_STRICTNESS=high \
    bimigrator:enhanced \
    ./bimigrator-enhanced migrate-module \
    --module-id "MODULE_ID" \
    --output-path "/app/output" \
    --cognos-url "http://server:9300/api/v1" \
    --session-key "SESSION_KEY" \
    --enable-enhanced-validation
```

## Troubleshooting

### Common Issues

1. **Session Key Expired**
   ```
   Error: Session key is invalid or expired
   ```
   Solution: Obtain a new session key from Cognos

2. **Module Not Found**
   ```
   Error: Module not found
   ```
   Solution: Verify module ID and permissions

3. **Validation Failures**
   ```
   Warning: Validation failed for X expressions
   ```
   Solution: Check validation report for details

### Debug Mode
Enable debug output for troubleshooting:

```bash
./bimigrator-enhanced migrate-module \
    --module-id "MODULE_ID" \
    --output-path "./output" \
    --cognos-url "http://server:9300/api/v1" \
    --session-key "SESSION_KEY" \
    --debug
```

### Log Files
Check these locations for logs:
- Error log: Specified by `--error-log-path`
- Validation report: `<output_path>/validation_report.json`
- Quality report: `<output_path>/quality_report.html`
- Migration metrics: `migration_metrics.db` (SQLite database)

## Best Practices

1. **Always Test Connection First**
   ```bash
   ./bimigrator-enhanced test-connection --cognos-url <url> --session-key <key>
   ```

2. **Use Validation Before Migration**
   ```bash
   ./bimigrator-enhanced validate-module --module-id <id> ...
   ```

3. **Enable Enhanced Validation for Production**
   ```bash
   --enable-enhanced-validation --validation-config '{"validation_strictness": "high"}'
   ```

4. **Monitor Progress with WebSocket**
   ```bash
   --enable-websocket --websocket-url "ws://localhost:8765"
   ```

5. **Generate Quality Reports**
   ```bash
   ./bimigrator-enhanced post-process ... --generate-quality-report
   ```

6. **Use Configuration Files for Consistency**
   ```bash
   --config-file production_config.json
   ```

7. **Keep Error Logs**
   ```bash
   --error-log-path "./migration_errors.log"
   ```

## Support

For issues or questions:
1. Check the validation report for specific errors
2. Review error logs with `--debug` flag
3. Consult the main BIMigrator-Cognos documentation
4. Use `--help` for command-specific help

```bash
# General help
./bimigrator-enhanced --help

# Command-specific help
./bimigrator-enhanced migrate-module --help
```