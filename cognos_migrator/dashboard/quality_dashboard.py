"""
Migration Quality Metrics Dashboard

This module provides a web-based dashboard for monitoring migration quality,
validation success rates, and performance metrics in real-time.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import sqlite3
from dataclasses import dataclass, asdict
from flask import Flask, render_template, jsonify, request, send_from_directory

# Import reporting components
from cognos_migrator.reporting.migration_reporter import MigrationReporter
from cognos_migrator.reporting.validation_report import ValidationReport


@dataclass
class MigrationMetrics:
    """Data class for migration metrics"""
    timestamp: str
    module_id: str
    total_expressions: int
    successful_conversions: int
    failed_conversions: int
    fallback_used: int
    validation_success_rate: float
    conversion_success_rate: float
    processing_time: float
    memory_usage: float
    error_count: int


@dataclass
class DashboardData:
    """Data class for dashboard data"""
    overview: Dict[str, Any]
    recent_migrations: List[MigrationMetrics]
    success_trends: List[Dict[str, Any]]
    error_analysis: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    validation_insights: Dict[str, Any]


class MetricsDatabase:
    """Database handler for storing migration metrics"""
    
    def __init__(self, db_path: str = "migration_metrics.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the metrics database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS migration_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    module_id TEXT NOT NULL,
                    total_expressions INTEGER,
                    successful_conversions INTEGER,
                    failed_conversions INTEGER,
                    fallback_used INTEGER,
                    validation_success_rate REAL,
                    conversion_success_rate REAL,
                    processing_time REAL,
                    memory_usage REAL,
                    error_count INTEGER,
                    raw_data TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS validation_details (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    migration_id INTEGER,
                    expression_type TEXT,
                    original_expression TEXT,
                    converted_expression TEXT,
                    validation_result TEXT,
                    fallback_used BOOLEAN,
                    error_message TEXT,
                    FOREIGN KEY (migration_id) REFERENCES migration_metrics (id)
                )
            ''')
    
    def store_migration_metrics(self, metrics: MigrationMetrics, raw_data: Dict = None) -> int:
        """Store migration metrics in database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT INTO migration_metrics (
                    timestamp, module_id, total_expressions, successful_conversions,
                    failed_conversions, fallback_used, validation_success_rate,
                    conversion_success_rate, processing_time, memory_usage,
                    error_count, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metrics.timestamp, metrics.module_id, metrics.total_expressions,
                metrics.successful_conversions, metrics.failed_conversions,
                metrics.fallback_used, metrics.validation_success_rate,
                metrics.conversion_success_rate, metrics.processing_time,
                metrics.memory_usage, metrics.error_count,
                json.dumps(raw_data) if raw_data else None
            ))
            return cursor.lastrowid
    
    def get_recent_migrations(self, limit: int = 50) -> List[MigrationMetrics]:
        """Get recent migration metrics"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM migration_metrics 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            
            results = []
            for row in cursor.fetchall():
                metrics = MigrationMetrics(
                    timestamp=row['timestamp'],
                    module_id=row['module_id'],
                    total_expressions=row['total_expressions'],
                    successful_conversions=row['successful_conversions'],
                    failed_conversions=row['failed_conversions'],
                    fallback_used=row['fallback_used'],
                    validation_success_rate=row['validation_success_rate'],
                    conversion_success_rate=row['conversion_success_rate'],
                    processing_time=row['processing_time'],
                    memory_usage=row['memory_usage'],
                    error_count=row['error_count']
                )
                results.append(metrics)
            
            return results
    
    def get_success_trends(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get success rate trends over time"""
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT 
                    DATE(timestamp) as date,
                    AVG(validation_success_rate) as avg_validation_rate,
                    AVG(conversion_success_rate) as avg_conversion_rate,
                    COUNT(*) as migration_count
                FROM migration_metrics 
                WHERE timestamp >= ?
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            ''', (cutoff_date,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_error_analysis(self) -> Dict[str, Any]:
        """Get error analysis data"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get most common error patterns
            cursor = conn.execute('''
                SELECT 
                    error_message,
                    COUNT(*) as count
                FROM validation_details 
                WHERE error_message IS NOT NULL
                GROUP BY error_message
                ORDER BY count DESC
                LIMIT 10
            ''')
            common_errors = [dict(row) for row in cursor.fetchall()]
            
            # Get error trends
            cursor = conn.execute('''
                SELECT 
                    DATE(timestamp) as date,
                    SUM(error_count) as total_errors
                FROM migration_metrics 
                WHERE timestamp >= DATE('now', '-30 days')
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            ''')
            error_trends = [dict(row) for row in cursor.fetchall()]
            
            return {
                'common_errors': common_errors,
                'error_trends': error_trends
            }


class QualityDashboard:
    """Main dashboard class for migration quality metrics"""
    
    def __init__(self, db_path: str = "migration_metrics.db", 
                 output_directory: str = "./dashboard_output"):
        self.db = MetricsDatabase(db_path)
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(exist_ok=True)
        
        # Initialize Flask app
        self.app = Flask(__name__, 
                        template_folder=str(self.output_directory / "templates"),
                        static_folder=str(self.output_directory / "static"))
        self.setup_routes()
    
    def setup_routes(self):
        """Setup Flask routes for the dashboard"""
        
        @self.app.route('/')
        def dashboard():
            """Main dashboard page"""
            return render_template('dashboard.html')
        
        @self.app.route('/api/dashboard-data')
        def get_dashboard_data():
            """API endpoint for dashboard data"""
            data = self.generate_dashboard_data()
            return jsonify(asdict(data))
        
        @self.app.route('/api/migration-details/<migration_id>')
        def get_migration_details(migration_id):
            """API endpoint for detailed migration data"""
            details = self.get_migration_details(migration_id)
            return jsonify(details)
        
        @self.app.route('/api/export-metrics')
        def export_metrics():
            """API endpoint to export metrics"""
            format_type = request.args.get('format', 'json')
            return self.export_metrics(format_type)
        
        @self.app.route('/static/<path:filename>')
        def static_files(filename):
            """Serve static files"""
            return send_from_directory(self.output_directory / "static", filename)
    
    def record_migration_metrics(self, migration_data: Dict[str, Any]) -> int:
        """Record migration metrics from migration data"""
        # Extract metrics from migration data
        validation_results = migration_data.get('validation_results', {})
        performance_data = migration_data.get('performance_metrics', {})
        
        metrics = MigrationMetrics(
            timestamp=migration_data.get('timestamp', datetime.now().isoformat()),
            module_id=migration_data.get('module_id', 'unknown'),
            total_expressions=validation_results.get('total_expressions', 0),
            successful_conversions=validation_results.get('successful_conversions', 0),
            failed_conversions=validation_results.get('failed_conversions', 0),
            fallback_used=validation_results.get('fallbacks_used', 0),
            validation_success_rate=validation_results.get('validation_success_rate', 0.0),
            conversion_success_rate=validation_results.get('conversion_success_rate', 0.0),
            processing_time=performance_data.get('processing_time', 0.0),
            memory_usage=performance_data.get('memory_usage', 0.0),
            error_count=validation_results.get('error_count', 0)
        )
        
        return self.db.store_migration_metrics(metrics, migration_data)
    
    def generate_dashboard_data(self) -> DashboardData:
        """Generate comprehensive dashboard data"""
        recent_migrations = self.db.get_recent_migrations(limit=20)
        success_trends = self.db.get_success_trends(days=30)
        error_analysis = self.db.get_error_analysis()
        
        # Calculate overview metrics
        overview = self.calculate_overview_metrics(recent_migrations)
        
        # Calculate performance metrics
        performance_metrics = self.calculate_performance_metrics(recent_migrations)
        
        # Generate validation insights
        validation_insights = self.generate_validation_insights(recent_migrations)
        
        return DashboardData(
            overview=overview,
            recent_migrations=recent_migrations,
            success_trends=success_trends,
            error_analysis=error_analysis,
            performance_metrics=performance_metrics,
            validation_insights=validation_insights
        )
    
    def calculate_overview_metrics(self, migrations: List[MigrationMetrics]) -> Dict[str, Any]:
        """Calculate overview metrics from recent migrations"""
        if not migrations:
            return {
                'total_migrations': 0,
                'avg_success_rate': 0.0,
                'total_expressions_processed': 0,
                'fallback_usage_rate': 0.0,
                'avg_processing_time': 0.0
            }
        
        total_migrations = len(migrations)
        total_expressions = sum(m.total_expressions for m in migrations)
        total_fallbacks = sum(m.fallback_used for m in migrations)
        avg_validation_rate = sum(m.validation_success_rate for m in migrations) / total_migrations
        avg_conversion_rate = sum(m.conversion_success_rate for m in migrations) / total_migrations
        avg_processing_time = sum(m.processing_time for m in migrations) / total_migrations
        
        return {
            'total_migrations': total_migrations,
            'avg_validation_success_rate': round(avg_validation_rate * 100, 2),
            'avg_conversion_success_rate': round(avg_conversion_rate * 100, 2),
            'total_expressions_processed': total_expressions,
            'fallback_usage_rate': round((total_fallbacks / total_expressions * 100) if total_expressions > 0 else 0, 2),
            'avg_processing_time': round(avg_processing_time, 2)
        }
    
    def calculate_performance_metrics(self, migrations: List[MigrationMetrics]) -> Dict[str, Any]:
        """Calculate performance metrics"""
        if not migrations:
            return {}
        
        processing_times = [m.processing_time for m in migrations]
        memory_usage = [m.memory_usage for m in migrations if m.memory_usage > 0]
        expressions_per_second = [
            m.total_expressions / m.processing_time 
            for m in migrations 
            if m.processing_time > 0
        ]
        
        return {
            'avg_processing_time': round(sum(processing_times) / len(processing_times), 2),
            'max_processing_time': round(max(processing_times), 2),
            'min_processing_time': round(min(processing_times), 2),
            'avg_memory_usage': round(sum(memory_usage) / len(memory_usage), 2) if memory_usage else 0,
            'avg_expressions_per_second': round(sum(expressions_per_second) / len(expressions_per_second), 2) if expressions_per_second else 0
        }
    
    def generate_validation_insights(self, migrations: List[MigrationMetrics]) -> Dict[str, Any]:
        """Generate validation insights and recommendations"""
        if not migrations:
            return {}
        
        # Calculate success rates by category
        high_success_migrations = [m for m in migrations if m.validation_success_rate > 0.9]
        medium_success_migrations = [m for m in migrations if 0.7 <= m.validation_success_rate <= 0.9]
        low_success_migrations = [m for m in migrations if m.validation_success_rate < 0.7]
        
        # Calculate fallback patterns
        high_fallback_migrations = [m for m in migrations if m.fallback_used / m.total_expressions > 0.3]
        
        insights = {
            'success_distribution': {
                'high_success': len(high_success_migrations),
                'medium_success': len(medium_success_migrations),
                'low_success': len(low_success_migrations)
            },
            'fallback_analysis': {
                'high_fallback_count': len(high_fallback_migrations),
                'avg_fallback_rate': round(
                    sum(m.fallback_used / m.total_expressions for m in migrations if m.total_expressions > 0) / len(migrations) * 100, 2
                )
            },
            'recommendations': self.generate_recommendations(migrations)
        }
        
        return insights
    
    def generate_recommendations(self, migrations: List[MigrationMetrics]) -> List[str]:
        """Generate actionable recommendations based on metrics"""
        recommendations = []
        
        if not migrations:
            return recommendations
        
        avg_success_rate = sum(m.validation_success_rate for m in migrations) / len(migrations)
        avg_fallback_rate = sum(m.fallback_used / m.total_expressions for m in migrations if m.total_expressions > 0) / len(migrations)
        
        if avg_success_rate < 0.8:
            recommendations.append("Consider reviewing validation rules - success rate is below 80%")
        
        if avg_fallback_rate > 0.4:
            recommendations.append("High fallback usage detected - review expression complexity")
        
        high_processing_times = [m for m in migrations if m.processing_time > 60]  # More than 1 minute
        if len(high_processing_times) > len(migrations) * 0.2:  # More than 20% are slow
            recommendations.append("Performance optimization needed - many migrations taking >60 seconds")
        
        error_prone_migrations = [m for m in migrations if m.error_count > 10]
        if error_prone_migrations:
            recommendations.append("Investigate error patterns - some migrations have high error counts")
        
        return recommendations
    
    def get_migration_details(self, migration_id: str) -> Dict[str, Any]:
        """Get detailed information for a specific migration"""
        # This would fetch detailed validation results, expression-level data, etc.
        # Implementation depends on how detailed data is stored
        return {
            'migration_id': migration_id,
            'detailed_results': 'Implementation needed based on storage schema'
        }
    
    def export_metrics(self, format_type: str = 'json') -> str:
        """Export metrics in specified format"""
        recent_migrations = self.db.get_recent_migrations(limit=100)
        
        if format_type.lower() == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                'timestamp', 'module_id', 'total_expressions', 'successful_conversions',
                'validation_success_rate', 'conversion_success_rate', 'processing_time'
            ])
            
            # Write data
            for migration in recent_migrations:
                writer.writerow([
                    migration.timestamp, migration.module_id, migration.total_expressions,
                    migration.successful_conversions, migration.validation_success_rate,
                    migration.conversion_success_rate, migration.processing_time
                ])
            
            return output.getvalue()
        
        else:  # JSON format
            return json.dumps([asdict(m) for m in recent_migrations], indent=2)
    
    def create_dashboard_templates(self):
        """Create HTML templates for the dashboard"""
        templates_dir = self.output_directory / "templates"
        templates_dir.mkdir(exist_ok=True)
        
        # Create main dashboard template
        dashboard_html = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Migration Quality Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .metric-card { margin-bottom: 20px; }
        .chart-container { height: 400px; margin-bottom: 30px; }
        .recommendations { background-color: #f8f9fa; padding: 15px; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <div class="col-12">
                <h1 class="mb-4">Migration Quality Dashboard</h1>
            </div>
        </div>
        
        <!-- Overview Cards -->
        <div class="row" id="overview-cards">
            <!-- Cards will be populated by JavaScript -->
        </div>
        
        <!-- Charts -->
        <div class="row">
            <div class="col-md-6">
                <div class="chart-container">
                    <canvas id="successTrendChart"></canvas>
                </div>
            </div>
            <div class="col-md-6">
                <div class="chart-container">
                    <canvas id="performanceChart"></canvas>
                </div>
            </div>
        </div>
        
        <!-- Migration History -->
        <div class="row">
            <div class="col-12">
                <h3>Recent Migrations</h3>
                <div class="table-responsive">
                    <table class="table table-striped" id="migrations-table">
                        <thead>
                            <tr>
                                <th>Timestamp</th>
                                <th>Module ID</th>
                                <th>Expressions</th>
                                <th>Success Rate</th>
                                <th>Fallback Usage</th>
                                <th>Processing Time</th>
                            </tr>
                        </thead>
                        <tbody id="migrations-tbody">
                            <!-- Rows will be populated by JavaScript -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        
        <!-- Recommendations -->
        <div class="row">
            <div class="col-12">
                <div class="recommendations">
                    <h4>Recommendations</h4>
                    <ul id="recommendations-list">
                        <!-- Recommendations will be populated by JavaScript -->
                    </ul>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Dashboard JavaScript
        let dashboardData = {};
        
        // Fetch dashboard data
        async function loadDashboardData() {
            try {
                const response = await fetch('/api/dashboard-data');
                dashboardData = await response.json();
                updateDashboard();
            } catch (error) {
                console.error('Error loading dashboard data:', error);
            }
        }
        
        // Update dashboard with data
        function updateDashboard() {
            updateOverviewCards();
            updateCharts();
            updateMigrationsTable();
            updateRecommendations();
        }
        
        // Update overview cards
        function updateOverviewCards() {
            const overview = dashboardData.overview;
            const cardsHtml = `
                <div class="col-md-3">
                    <div class="card metric-card">
                        <div class="card-body">
                            <h5 class="card-title">Total Migrations</h5>
                            <h2 class="text-primary">${overview.total_migrations}</h2>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card metric-card">
                        <div class="card-body">
                            <h5 class="card-title">Avg Success Rate</h5>
                            <h2 class="text-success">${overview.avg_validation_success_rate}%</h2>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card metric-card">
                        <div class="card-body">
                            <h5 class="card-title">Expressions Processed</h5>
                            <h2 class="text-info">${overview.total_expressions_processed}</h2>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card metric-card">
                        <div class="card-body">
                            <h5 class="card-title">Fallback Usage</h5>
                            <h2 class="text-warning">${overview.fallback_usage_rate}%</h2>
                        </div>
                    </div>
                </div>
            `;
            document.getElementById('overview-cards').innerHTML = cardsHtml;
        }
        
        // Update charts
        function updateCharts() {
            // Success trend chart
            const successCtx = document.getElementById('successTrendChart').getContext('2d');
            new Chart(successCtx, {
                type: 'line',
                data: {
                    labels: dashboardData.success_trends.map(t => t.date),
                    datasets: [{
                        label: 'Validation Success Rate',
                        data: dashboardData.success_trends.map(t => t.avg_validation_rate * 100),
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1
                    }, {
                        label: 'Conversion Success Rate',
                        data: dashboardData.success_trends.map(t => t.avg_conversion_rate * 100),
                        borderColor: 'rgb(255, 99, 132)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { title: { display: true, text: 'Success Rate Trends' } },
                    scales: { y: { beginAtZero: true, max: 100 } }
                }
            });
            
            // Performance chart
            const perfCtx = document.getElementById('performanceChart').getContext('2d');
            new Chart(perfCtx, {
                type: 'bar',
                data: {
                    labels: ['Avg Processing Time', 'Max Processing Time', 'Expressions/Second'],
                    datasets: [{
                        label: 'Performance Metrics',
                        data: [
                            dashboardData.performance_metrics.avg_processing_time,
                            dashboardData.performance_metrics.max_processing_time,
                            dashboardData.performance_metrics.avg_expressions_per_second
                        ],
                        backgroundColor: ['rgba(54, 162, 235, 0.5)', 'rgba(255, 99, 132, 0.5)', 'rgba(75, 192, 192, 0.5)']
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { title: { display: true, text: 'Performance Metrics' } }
                }
            });
        }
        
        // Update migrations table
        function updateMigrationsTable() {
            const tbody = document.getElementById('migrations-tbody');
            const rowsHtml = dashboardData.recent_migrations.map(migration => `
                <tr>
                    <td>${new Date(migration.timestamp).toLocaleString()}</td>
                    <td>${migration.module_id}</td>
                    <td>${migration.total_expressions}</td>
                    <td>${(migration.validation_success_rate * 100).toFixed(1)}%</td>
                    <td>${((migration.fallback_used / migration.total_expressions) * 100).toFixed(1)}%</td>
                    <td>${migration.processing_time.toFixed(2)}s</td>
                </tr>
            `).join('');
            tbody.innerHTML = rowsHtml;
        }
        
        // Update recommendations
        function updateRecommendations() {
            const list = document.getElementById('recommendations-list');
            const recommendations = dashboardData.validation_insights.recommendations;
            const itemsHtml = recommendations.map(rec => `<li>${rec}</li>`).join('');
            list.innerHTML = itemsHtml;
        }
        
        // Load data on page load
        document.addEventListener('DOMContentLoaded', loadDashboardData);
        
        // Refresh data every 30 seconds
        setInterval(loadDashboardData, 30000);
    </script>
</body>
</html>
        '''
        
        with open(templates_dir / "dashboard.html", "w") as f:
            f.write(dashboard_html)
    
    def run_dashboard(self, host: str = '0.0.0.0', port: int = 5000, debug: bool = False):
        """Run the Flask dashboard server"""
        self.create_dashboard_templates()
        print(f"Starting Migration Quality Dashboard at http://{host}:{port}")
        self.app.run(host=host, port=port, debug=debug)


# Utility functions for integration
def integrate_with_migration(migration_result: Dict[str, Any], 
                           dashboard: QualityDashboard) -> int:
    """Integrate migration results with the quality dashboard"""
    return dashboard.record_migration_metrics(migration_result)


def create_standalone_dashboard(db_path: str = None) -> QualityDashboard:
    """Create a standalone dashboard instance"""
    if db_path is None:
        db_path = str(Path.cwd() / "migration_metrics.db")
    
    dashboard = QualityDashboard(db_path=db_path)
    return dashboard


if __name__ == "__main__":
    # Run standalone dashboard
    dashboard = create_standalone_dashboard()
    dashboard.run_dashboard(debug=True)