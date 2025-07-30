"""
Validation-specific reporting components
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ValidationIssue:
    """Represents a validation issue"""
    type: str  # "syntax", "semantic", "performance", etc.
    severity: str  # "error", "warning", "info"
    message: str
    expression: str
    suggestion: Optional[str] = None


class ValidationReport:
    """Generate detailed validation reports"""
    
    def __init__(self):
        self.issues: List[ValidationIssue] = []
        self.validation_stats = {
            "total_validations": 0,
            "passed": 0,
            "failed": 0,
            "warnings": 0
        }
    
    def add_validation_result(self, 
                            expression: str,
                            is_valid: bool,
                            issues: List[str],
                            warnings: List[str]):
        """Add validation result"""
        self.validation_stats["total_validations"] += 1
        
        if is_valid:
            self.validation_stats["passed"] += 1
        else:
            self.validation_stats["failed"] += 1
        
        # Process issues
        for issue in issues:
            self.issues.append(ValidationIssue(
                type="error",
                severity="error",
                message=issue,
                expression=expression[:100] + "..." if len(expression) > 100 else expression
            ))
        
        # Process warnings
        for warning in warnings:
            self.issues.append(ValidationIssue(
                type="warning",
                severity="warning", 
                message=warning,
                expression=expression[:100] + "..." if len(expression) > 100 else expression
            ))
            self.validation_stats["warnings"] += 1
    
    def generate_validation_summary(self) -> Dict[str, Any]:
        """Generate validation summary"""
        # Group issues by type and message
        issue_frequency = {}
        for issue in self.issues:
            key = f"{issue.type}: {issue.message}"
            issue_frequency[key] = issue_frequency.get(key, 0) + 1
        
        # Sort by frequency
        top_issues = sorted(issue_frequency.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "statistics": self.validation_stats,
            "success_rate": self.validation_stats["passed"] / max(self.validation_stats["total_validations"], 1),
            "top_issues": [{"issue": issue, "count": count} for issue, count in top_issues],
            "total_issues": len(self.issues),
            "issues_by_severity": {
                "error": len([i for i in self.issues if i.severity == "error"]),
                "warning": len([i for i in self.issues if i.severity == "warning"]),
                "info": len([i for i in self.issues if i.severity == "info"])
            }
        }
    
    def generate_detailed_issues_report(self) -> List[Dict[str, Any]]:
        """Generate detailed issues report"""
        return [
            {
                "type": issue.type,
                "severity": issue.severity,
                "message": issue.message,
                "expression": issue.expression,
                "suggestion": issue.suggestion
            }
            for issue in self.issues
        ]
    
    def get_fix_recommendations(self) -> List[Dict[str, str]]:
        """Generate fix recommendations based on common issues"""
        recommendations = []
        
        # Analyze common patterns
        error_patterns = {}
        for issue in self.issues:
            if issue.severity == "error":
                error_patterns[issue.message] = error_patterns.get(issue.message, 0) + 1
        
        # Generate recommendations based on frequency
        for error_msg, count in sorted(error_patterns.items(), key=lambda x: x[1], reverse=True)[:5]:
            if "unbalanced" in error_msg.lower():
                recommendations.append({
                    "issue": error_msg,
                    "frequency": str(count),
                    "recommendation": "Check for missing parentheses, brackets, or quotes in expressions",
                    "priority": "high"
                })
            elif "unknown" in error_msg.lower() and "function" in error_msg.lower():
                recommendations.append({
                    "issue": error_msg,
                    "frequency": str(count),
                    "recommendation": "Verify function names and consider adding function mappings",
                    "priority": "medium"
                })
            elif "table" in error_msg.lower() or "column" in error_msg.lower():
                recommendations.append({
                    "issue": error_msg,
                    "frequency": str(count),
                    "recommendation": "Verify table and column references exist in the target schema",
                    "priority": "high"
                })
        
        return recommendations