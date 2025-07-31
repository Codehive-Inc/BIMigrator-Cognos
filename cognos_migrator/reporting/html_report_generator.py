"""
HTML report generator for migration results
"""

from typing import Dict, Any
import html


class HTMLReportGenerator:
    """Generates HTML reports for migration results"""
    
    def generate_html_report(self, report_data: Dict[str, Any]) -> str:
        """Generate HTML report from report data"""
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cognos to Power BI Migration Report</title>
    <style>
        {self._get_css_styles()}
    </style>
</head>
<body>
    <div class="container">
        {self._generate_header(report_data)}
        {self._generate_summary(report_data)}
        {self._generate_statistics(report_data)}
        {self._generate_recommendations(report_data)}
        {self._generate_samples(report_data)}
        {self._generate_validation_details(report_data)}
    </div>
    
    <script>
        {self._get_javascript()}
    </script>
</body>
</html>
"""
        return html_content
    
    def _get_css_styles(self) -> str:
        """Get CSS styles for the report"""
        return """
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        h1, h2, h3 {
            color: #2c3e50;
        }
        
        h1 {
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .metric-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border-left: 4px solid #3498db;
        }
        
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: #2c3e50;
        }
        
        .metric-label {
            color: #7f8c8d;
            margin-top: 5px;
        }
        
        .success-rate {
            border-left-color: #27ae60;
        }
        
        .success-rate .metric-value {
            color: #27ae60;
        }
        
        .warning-rate {
            border-left-color: #f39c12;
        }
        
        .warning-rate .metric-value {
            color: #f39c12;
        }
        
        .error-rate {
            border-left-color: #e74c3c;
        }
        
        .error-rate .metric-value {
            color: #e74c3c;
        }
        
        .chart-container {
            margin: 20px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        
        .progress-bar {
            background: #ecf0f1;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }
        
        .progress-fill {
            height: 20px;
            background: linear-gradient(90deg, #3498db, #2980b9);
            transition: width 0.5s ease;
        }
        
        .recommendations {
            margin: 30px 0;
        }
        
        .recommendation {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 5px;
            padding: 15px;
            margin: 10px 0;
        }
        
        .recommendation.high {
            background: #f8d7da;
            border-color: #f5c6cb;
        }
        
        .recommendation.medium {
            background: #fff3cd;
            border-color: #ffeaa7;
        }
        
        .recommendation.low {
            background: #d1ecf1;
            border-color: #b8daff;
        }
        
        .sample-conversion {
            background: #f8f9fa;
            border-radius: 5px;
            padding: 15px;
            margin: 10px 0;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }
        
        .conversion-original {
            color: #e74c3c;
            margin-bottom: 10px;
        }
        
        .conversion-result {
            color: #27ae60;
            margin-top: 10px;
        }
        
        .badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: bold;
            margin: 2px;
        }
        
        .badge-success {
            background: #d4edda;
            color: #155724;
        }
        
        .badge-warning {
            background: #fff3cd;
            color: #856404;
        }
        
        .badge-danger {
            background: #f8d7da;
            color: #721c24;
        }
        
        .collapsible {
            cursor: pointer;
            padding: 10px;
            background: #3498db;
            color: white;
            border: none;
            border-radius: 5px;
            width: 100%;
            text-align: left;
            margin: 10px 0;
        }
        
        .collapsible:hover {
            background: #2980b9;
        }
        
        .content {
            padding: 0 15px;
            display: none;
            overflow: hidden;
            background: #f8f9fa;
            border-radius: 0 0 5px 5px;
        }
        
        .content.active {
            display: block;
            padding: 15px;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        
        th, td {
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }
        
        th {
            background: #3498db;
            color: white;
        }
        
        tr:nth-child(even) {
            background: #f2f2f2;
        }
        """
    
    def _generate_header(self, report_data: Dict[str, Any]) -> str:
        """Generate report header"""
        metadata = report_data.get("metadata", {})
        
        return f"""
        <h1>🔄 Cognos to Power BI Migration Report</h1>
        <div class="metadata">
            <p><strong>Generated:</strong> {metadata.get('report_generated', 'Unknown')}</p>
            <p><strong>Migration Duration:</strong> {metadata.get('migration_duration_seconds', 0):.1f} seconds</p>
            <p><strong>Total Tables:</strong> {metadata.get('total_tables', 0)}</p>
            <p><strong>Total Expressions:</strong> {metadata.get('total_expressions', 0)}</p>
        </div>
        """
    
    def _generate_summary(self, report_data: Dict[str, Any]) -> str:
        """Generate summary section"""
        summary = report_data.get("summary", {})
        
        success_rate = summary.get("overall_success_rate", 0)
        fallbacks = summary.get("fallbacks_applied", 0)
        manual_review = summary.get("manual_review_required", 0)
        
        success_class = "success-rate" if success_rate >= 0.8 else "warning-rate" if success_rate >= 0.6 else "error-rate"
        
        return f"""
        <h2>📊 Migration Summary</h2>
        <div class="summary-grid">
            <div class="metric-card {success_class}">
                <div class="metric-value">{success_rate:.1%}</div>
                <div class="metric-label">Success Rate</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{summary.get('tables_migrated', 0)}</div>
                <div class="metric-label">Tables Migrated</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{summary.get('expressions_converted', 0)}</div>
                <div class="metric-label">Expressions Converted</div>
            </div>
            <div class="metric-card warning-rate">
                <div class="metric-value">{fallbacks}</div>
                <div class="metric-label">Fallbacks Applied</div>
            </div>
            <div class="metric-card error-rate">
                <div class="metric-value">{manual_review}</div>
                <div class="metric-label">Manual Review Required</div>
            </div>
        </div>
        """
    
    def _generate_statistics(self, report_data: Dict[str, Any]) -> str:
        """Generate statistics section"""
        conv_stats = report_data.get("conversion_statistics", {})
        
        if not conv_stats or "message" in conv_stats:
            return "<h2>📈 Statistics</h2><p>No conversion statistics available.</p>"
        
        # Strategy breakdown
        strategies_html = ""
        for strategy, count in conv_stats.get("by_strategy", {}).items():
            percentage = (count / conv_stats.get("total_conversions", 1)) * 100
            strategies_html += f"""
            <div class="progress-bar">
                <div class="progress-fill" style="width: {percentage}%"></div>
            </div>
            <p>{strategy}: {count} ({percentage:.1f}%)</p>
            """
        
        # Confidence statistics
        conf_stats = conv_stats.get("confidence_statistics", {})
        
        return f"""
        <h2>📈 Conversion Statistics</h2>
        
        <h3>Conversion Strategies Used</h3>
        <div class="chart-container">
            {strategies_html}
        </div>
        
        <h3>Confidence Distribution</h3>
        <div class="chart-container">
            <p>🟢 High Confidence (≥80%): {conf_stats.get('high_confidence_count', 0)}</p>
            <p>🟡 Medium Confidence (50-79%): {conf_stats.get('medium_confidence_count', 0)}</p>
            <p>🔴 Low Confidence (<50%): {conf_stats.get('low_confidence_count', 0)}</p>
            <p><strong>Average Confidence:</strong> {conf_stats.get('average_confidence', 0):.1%}</p>
        </div>
        """
    
    def _generate_recommendations(self, report_data: Dict[str, Any]) -> str:
        """Generate recommendations section"""
        recommendations = report_data.get("recommendations", [])
        
        if not recommendations:
            return """
            <h2>✅ Recommendations</h2>
            <p class="recommendation low">
                🎉 Great job! No major issues found in the migration. 
                Consider reviewing any items marked for manual review.
            </p>
            """
        
        recs_html = ""
        for rec in recommendations:
            severity_class = rec.get("severity", "low")
            icon = "🔴" if severity_class == "high" else "🟡" if severity_class == "medium" else "🔵"
            
            recs_html += f"""
            <div class="recommendation {severity_class}">
                <h4>{icon} {html.escape(rec.get('category', 'Recommendation'))}</h4>
                <p>{html.escape(rec.get('description', ''))}</p>
                <p><strong>Action:</strong> {html.escape(rec.get('action', ''))}</p>
            </div>
            """
        
        return f"""
        <h2>💡 Recommendations</h2>
        <div class="recommendations">
            {recs_html}
        </div>
        """
    
    def _generate_samples(self, report_data: Dict[str, Any]) -> str:
        """Generate sample conversions section"""
        samples = report_data.get("sample_conversions", [])
        
        if not samples:
            return "<h2>📝 Sample Conversions</h2><p>No sample conversions available.</p>"
        
        samples_html = ""
        for sample in samples:
            confidence = sample.get("confidence", 0)
            conf_badge = "success" if confidence >= 0.8 else "warning" if confidence >= 0.5 else "danger"
            fallback_badge = f'<span class="badge badge-warning">Fallback Applied</span>' if sample.get("fallback_applied") else ""
            
            samples_html += f"""
            <div class="sample-conversion">
                <h4>{html.escape(sample.get('strategy', 'Unknown Strategy'))} 
                    <span class="badge badge-{conf_badge}">Confidence: {confidence:.1%}</span>
                    {fallback_badge}
                </h4>
                <div class="conversion-original">
                    <strong>Original:</strong> {html.escape(sample.get('original', ''))}
                </div>
                <div class="conversion-result">
                    <strong>Converted:</strong> {html.escape(sample.get('converted', ''))}
                </div>
            </div>
            """
        
        return f"""
        <h2>📝 Sample Conversions</h2>
        {samples_html}
        """
    
    def _generate_validation_details(self, report_data: Dict[str, Any]) -> str:
        """Generate validation details section"""
        val_stats = report_data.get("validation_statistics", {})
        
        if not val_stats or "message" in val_stats:
            return ""
        
        # Common issues table
        issues_html = ""
        for issue, count in list(val_stats.get("common_issues", {}).items())[:10]:
            issues_html += f"""
            <tr>
                <td>{html.escape(issue)}</td>
                <td>{count}</td>
            </tr>
            """
        
        return f"""
        <button class="collapsible">🔍 Validation Details</button>
        <div class="content">
            <h3>Validation Results</h3>
            <p>✅ Passed: {val_stats.get('validation_passed', 0)}</p>
            <p>❌ Failed: {val_stats.get('validation_failed', 0)}</p>
            <p>📊 Success Rate: {val_stats.get('validation_rate', 0):.1%}</p>
            
            <h3>Most Common Issues</h3>
            <table>
                <thead>
                    <tr>
                        <th>Issue</th>
                        <th>Frequency</th>
                    </tr>
                </thead>
                <tbody>
                    {issues_html}
                </tbody>
            </table>
        </div>
        """
    
    def _get_javascript(self) -> str:
        """Get JavaScript for interactivity"""
        return """
        // Collapsible sections
        document.addEventListener('DOMContentLoaded', function() {
            var coll = document.getElementsByClassName("collapsible");
            for (var i = 0; i < coll.length; i++) {
                coll[i].addEventListener("click", function() {
                    this.classList.toggle("active");
                    var content = this.nextElementSibling;
                    content.classList.toggle("active");
                });
            }
            
            // Animate progress bars
            setTimeout(function() {
                var progressBars = document.querySelectorAll('.progress-fill');
                progressBars.forEach(function(bar) {
                    bar.style.width = bar.style.width;
                });
            }, 500);
        });
        """