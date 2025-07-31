"""
Enhanced migration reporting with validation results and fallback tracking
"""

import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum

from cognos_migrator.strategies import ConversionResult, FallbackTrigger, ConversionStrategy


class ReportFormat(Enum):
    """Report output formats"""
    JSON = "json"
    HTML = "html"
    CSV = "csv"
    MARKDOWN = "md"


@dataclass
class ReportConfig:
    """Configuration for migration reports"""
    include_successful_conversions: bool = True
    include_failed_conversions: bool = True
    include_fallback_details: bool = True
    include_validation_results: bool = True
    include_performance_metrics: bool = True
    include_recommendations: bool = True
    output_formats: List[ReportFormat] = field(default_factory=lambda: [ReportFormat.JSON, ReportFormat.HTML])
    max_sample_expressions: int = 10


class MigrationReporter:
    """Enhanced migration reporter with validation and fallback tracking"""
    
    def __init__(self, config: Optional[ReportConfig] = None, logger: Optional[logging.Logger] = None):
        self.config = config or ReportConfig()
        self.logger = logger or logging.getLogger(__name__)
        
        # Track migration data
        self.migration_start_time = datetime.now()
        self.migration_end_time = None
        self.conversion_results: List[ConversionResult] = []
        self.table_results: List[Dict[str, Any]] = []
        self.migration_metadata: Dict[str, Any] = {}
        
    def add_conversion_result(self, result: ConversionResult):
        """Add a conversion result to the report"""
        self.conversion_results.append(result)
    
    def add_table_result(self, table_name: str, 
                        mquery_result: Optional[str] = None,
                        expressions: Optional[List[ConversionResult]] = None,
                        validation_results: Optional[Dict[str, Any]] = None,
                        fallback_applied: bool = False):
        """Add table migration results"""
        table_result = {
            "table_name": table_name,
            "mquery_result": mquery_result,
            "mquery_length": len(mquery_result) if mquery_result else 0,
            "expressions": expressions or [],
            "expression_count": len(expressions) if expressions else 0,
            "validation_results": validation_results or {},
            "fallback_applied": fallback_applied,
            "timestamp": datetime.now().isoformat()
        }
        self.table_results.append(table_result)
    
    def set_migration_metadata(self, metadata: Dict[str, Any]):
        """Set migration metadata (project info, configuration, etc.)"""
        self.migration_metadata.update(metadata)
    
    def complete_migration(self):
        """Mark migration as complete"""
        self.migration_end_time = datetime.now()
    
    def generate_comprehensive_report(self, output_dir: str) -> Dict[str, str]:
        """
        Generate comprehensive migration report in all configured formats
        
        Args:
            output_dir: Directory to save reports
            
        Returns:
            Dictionary mapping format to file path
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate core report data
        report_data = self._build_report_data()
        
        # Generate reports in requested formats
        generated_files = {}
        
        for format_type in self.config.output_formats:
            if format_type == ReportFormat.JSON:
                file_path = self._generate_json_report(report_data, output_path)
                generated_files["json"] = str(file_path)
            
            elif format_type == ReportFormat.HTML:
                file_path = self._generate_html_report(report_data, output_path)
                generated_files["html"] = str(file_path)
            
            elif format_type == ReportFormat.CSV:
                file_path = self._generate_csv_report(report_data, output_path)
                generated_files["csv"] = str(file_path)
            
            elif format_type == ReportFormat.MARKDOWN:
                file_path = self._generate_markdown_report(report_data, output_path)
                generated_files["markdown"] = str(file_path)
        
        self.logger.info(f"Generated migration reports: {list(generated_files.keys())}")
        return generated_files
    
    def _build_report_data(self) -> Dict[str, Any]:
        """Build comprehensive report data structure"""
        
        # Calculate timing
        duration = None
        if self.migration_end_time:
            duration = (self.migration_end_time - self.migration_start_time).total_seconds()
        
        # Analyze conversion results
        conversion_stats = self._analyze_conversion_results()
        table_stats = self._analyze_table_results()
        validation_stats = self._analyze_validation_results()
        
        # Build report structure
        report_data = {
            "metadata": {
                "report_generated": datetime.now().isoformat(),
                "migration_start": self.migration_start_time.isoformat(),
                "migration_end": self.migration_end_time.isoformat() if self.migration_end_time else None,
                "migration_duration_seconds": duration,
                "total_tables": len(self.table_results),
                "total_expressions": len(self.conversion_results),
                **self.migration_metadata
            },
            "summary": {
                "overall_success_rate": self._calculate_overall_success_rate(),
                "tables_migrated": len(self.table_results),
                "expressions_converted": len(self.conversion_results),
                "fallbacks_applied": sum(1 for r in self.conversion_results if r.fallback_applied),
                "manual_review_required": sum(1 for r in self.conversion_results if r.requires_manual_review),
                "validation_enabled": any(r.validation_passed is not False for r in self.conversion_results)
            },
            "conversion_statistics": conversion_stats,
            "table_statistics": table_stats,
            "validation_statistics": validation_stats,
            "recommendations": self._generate_recommendations(),
            "sample_conversions": self._get_sample_conversions(),
            "raw_data": {
                "conversion_results": [self._serialize_conversion_result(r) for r in self.conversion_results],
                "table_results": self.table_results
            } if self.config.include_validation_results else {}
        }
        
        return report_data
    
    def _analyze_conversion_results(self) -> Dict[str, Any]:
        """Analyze conversion results for statistics"""
        if not self.conversion_results:
            return {"message": "No conversion results to analyze"}
        
        total = len(self.conversion_results)
        
        # Count by strategy
        strategy_counts = {}
        for strategy in ConversionStrategy:
            count = sum(1 for r in self.conversion_results if r.strategy_used == strategy)
            if count > 0:
                strategy_counts[strategy.value] = count
        
        # Count by fallback trigger
        fallback_trigger_counts = {}
        for trigger in FallbackTrigger:
            count = sum(1 for r in self.conversion_results 
                       if r.fallback_trigger == trigger)
            if count > 0:
                fallback_trigger_counts[trigger.value] = count
        
        # Count by expression type
        type_counts = {}
        for result in self.conversion_results:
            expr_type = result.expression_type
            type_counts[expr_type] = type_counts.get(expr_type, 0) + 1
        
        # Calculate confidence statistics
        confidence_scores = [r.confidence_score for r in self.conversion_results]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        return {
            "total_conversions": total,
            "by_strategy": strategy_counts,
            "by_fallback_trigger": fallback_trigger_counts,
            "by_expression_type": type_counts,
            "confidence_statistics": {
                "average_confidence": round(avg_confidence, 3),
                "high_confidence_count": sum(1 for s in confidence_scores if s >= 0.8),
                "medium_confidence_count": sum(1 for s in confidence_scores if 0.5 <= s < 0.8),
                "low_confidence_count": sum(1 for s in confidence_scores if s < 0.5)
            }
        }
    
    def _analyze_table_results(self) -> Dict[str, Any]:
        """Analyze table migration results"""
        if not self.table_results:
            return {"message": "No table results to analyze"}
        
        return {
            "total_tables": len(self.table_results),
            "tables_with_fallback": sum(1 for t in self.table_results if t.get("fallback_applied")),
            "average_expressions_per_table": sum(t.get("expression_count", 0) for t in self.table_results) / len(self.table_results),
            "average_mquery_length": sum(t.get("mquery_length", 0) for t in self.table_results) / len(self.table_results)
        }
    
    def _analyze_validation_results(self) -> Dict[str, Any]:
        """Analyze validation results"""
        validation_passed = sum(1 for r in self.conversion_results if r.validation_passed)
        validation_failed = sum(1 for r in self.conversion_results if not r.validation_passed)
        
        # Collect common issues
        all_issues = []
        for result in self.conversion_results:
            all_issues.extend(result.issues)
        
        # Count issue frequency
        issue_counts = {}
        for issue in all_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        return {
            "validation_passed": validation_passed,
            "validation_failed": validation_failed,
            "validation_rate": validation_passed / len(self.conversion_results) if self.conversion_results else 0,
            "common_issues": dict(sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:10])
        }
    
    def _calculate_overall_success_rate(self) -> float:
        """Calculate overall migration success rate"""
        if not self.conversion_results:
            return 1.0
        
        successful = sum(1 for r in self.conversion_results 
                        if r.strategy_used != ConversionStrategy.MANUAL_TEMPLATE)
        return successful / len(self.conversion_results)
    
    def _generate_recommendations(self) -> List[Dict[str, str]]:
        """Generate recommendations based on migration results"""
        recommendations = []
        
        # Analyze patterns and generate recommendations
        if not self.conversion_results:
            return recommendations
        
        fallback_rate = sum(1 for r in self.conversion_results if r.fallback_applied) / len(self.conversion_results)
        
        if fallback_rate > 0.3:
            recommendations.append({
                "category": "High Fallback Rate",
                "severity": "medium",
                "description": f"{fallback_rate:.1%} of conversions used fallbacks",
                "action": "Consider improving LLM prompts or adding more specific conversion rules"
            })
        
        low_confidence = sum(1 for r in self.conversion_results if r.confidence_score < 0.5)
        if low_confidence > 0:
            recommendations.append({
                "category": "Low Confidence Conversions",
                "severity": "high",
                "description": f"{low_confidence} conversions have low confidence scores",
                "action": "Review and manually verify low-confidence conversions"
            })
        
        manual_review_needed = sum(1 for r in self.conversion_results if r.requires_manual_review)
        if manual_review_needed > 0:
            recommendations.append({
                "category": "Manual Review Required",
                "severity": "high",
                "description": f"{manual_review_needed} conversions require manual review",
                "action": "Prioritize manual review of flagged conversions"
            })
        
        return recommendations
    
    def _get_sample_conversions(self) -> List[Dict[str, Any]]:
        """Get sample conversions for the report"""
        samples = []
        
        # Get examples of different strategies
        for strategy in ConversionStrategy:
            examples = [r for r in self.conversion_results if r.strategy_used == strategy][:2]
            for example in examples:
                samples.append({
                    "strategy": strategy.value,
                    "original": example.original_expression[:100] + "..." if len(example.original_expression) > 100 else example.original_expression,
                    "converted": example.converted_expression[:100] + "..." if len(example.converted_expression) > 100 else example.converted_expression,
                    "confidence": example.confidence_score,
                    "fallback_applied": example.fallback_applied
                })
        
        return samples[:self.config.max_sample_expressions]
    
    def _serialize_conversion_result(self, result: ConversionResult) -> Dict[str, Any]:
        """Serialize conversion result for JSON output"""
        return {
            "original_expression": result.original_expression,
            "converted_expression": result.converted_expression,
            "expression_type": result.expression_type,
            "strategy_used": result.strategy_used.value,
            "confidence_score": result.confidence_score,
            "validation_passed": result.validation_passed,
            "fallback_applied": result.fallback_applied,
            "fallback_trigger": result.fallback_trigger.value if result.fallback_trigger else None,
            "issues": result.issues,
            "warnings": result.warnings,
            "conversion_path": result.conversion_path,
            "requires_manual_review": result.requires_manual_review,
            "metadata": result.metadata
        }
    
    def _generate_json_report(self, report_data: Dict[str, Any], output_path: Path) -> Path:
        """Generate JSON report"""
        file_path = output_path / "migration_report.json"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        return file_path
    
    def _generate_html_report(self, report_data: Dict[str, Any], output_path: Path) -> Path:
        """Generate HTML report"""
        from .html_report_generator import HTMLReportGenerator
        
        generator = HTMLReportGenerator()
        html_content = generator.generate_html_report(report_data)
        
        file_path = output_path / "migration_report.html"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return file_path
    
    def _generate_csv_report(self, report_data: Dict[str, Any], output_path: Path) -> Path:
        """Generate CSV report of conversion results"""
        import csv
        
        file_path = output_path / "conversion_results.csv"
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            if self.conversion_results:
                writer = csv.DictWriter(f, fieldnames=[
                    'original_expression', 'converted_expression', 'expression_type',
                    'strategy_used', 'confidence_score', 'validation_passed',
                    'fallback_applied', 'requires_manual_review'
                ])
                writer.writeheader()
                
                for result in self.conversion_results:
                    writer.writerow({
                        'original_expression': result.original_expression[:200],
                        'converted_expression': result.converted_expression[:200],
                        'expression_type': result.expression_type,
                        'strategy_used': result.strategy_used.value,
                        'confidence_score': result.confidence_score,
                        'validation_passed': result.validation_passed,
                        'fallback_applied': result.fallback_applied,
                        'requires_manual_review': result.requires_manual_review
                    })
        
        return file_path
    
    def _generate_markdown_report(self, report_data: Dict[str, Any], output_path: Path) -> Path:
        """Generate Markdown report"""
        file_path = output_path / "migration_report.md"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("# Migration Report\n\n")
            
            # Summary
            summary = report_data["summary"]
            f.write("## Summary\n\n")
            f.write(f"- **Overall Success Rate**: {summary['overall_success_rate']:.1%}\n")
            f.write(f"- **Tables Migrated**: {summary['tables_migrated']}\n")
            f.write(f"- **Expressions Converted**: {summary['expressions_converted']}\n")
            f.write(f"- **Fallbacks Applied**: {summary['fallbacks_applied']}\n")
            f.write(f"- **Manual Review Required**: {summary['manual_review_required']}\n\n")
            
            # Recommendations
            if report_data["recommendations"]:
                f.write("## Recommendations\n\n")
                for rec in report_data["recommendations"]:
                    f.write(f"### {rec['category']} ({rec['severity']})\n")
                    f.write(f"{rec['description']}\n\n")
                    f.write(f"**Action**: {rec['action']}\n\n")
            
            # Sample conversions
            if report_data["sample_conversions"]:
                f.write("## Sample Conversions\n\n")
                for sample in report_data["sample_conversions"][:5]:
                    f.write(f"### {sample['strategy']}\n")
                    f.write(f"- **Original**: `{sample['original']}`\n")
                    f.write(f"- **Converted**: `{sample['converted']}`\n")
                    f.write(f"- **Confidence**: {sample['confidence']:.2f}\n\n")
        
        return file_path