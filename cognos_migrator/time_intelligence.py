"""
Time Intelligence Module for Cognos to Power BI Migration
Handles date calculations, fiscal year support, and time-based measures
"""

import re
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, date


class FiscalPeriodType(Enum):
    """Types of fiscal periods"""
    STANDARD = "standard"          # Jan-Dec
    APRIL_MARCH = "april_march"    # Apr-Mar (UK)
    JULY_JUNE = "july_june"        # Jul-Jun (Australia)
    OCTOBER_SEPTEMBER = "october_september"  # Oct-Sep (US Gov)
    CUSTOM = "custom"


class TimeIntelligenceType(Enum):
    """Types of time intelligence calculations"""
    YTD = "ytd"                    # Year to Date
    QTD = "qtd"                    # Quarter to Date
    MTD = "mtd"                    # Month to Date
    SAME_PERIOD_LAST_YEAR = "sply"  # Same Period Last Year
    PREVIOUS_YEAR = "py"           # Previous Year
    PREVIOUS_QUARTER = "pq"        # Previous Quarter
    PREVIOUS_MONTH = "pm"          # Previous Month
    ROLLING_AVERAGE = "rolling_avg" # Rolling Average
    PERCENT_CHANGE = "pct_change"  # Percentage Change


@dataclass
class FiscalYearConfig:
    """Configuration for fiscal year calculations"""
    start_month: int = 1           # 1 = January
    end_month: int = 12            # 12 = December
    start_day: int = 1
    end_day: int = 31
    fiscal_type: FiscalPeriodType = FiscalPeriodType.STANDARD
    year_offset: int = 0           # 0 = same as calendar year, 1 = year ahead


@dataclass
class TimeIntelligenceMeasure:
    """Represents a time intelligence measure"""
    name: str
    base_measure: str
    calculation_type: TimeIntelligenceType
    dax_expression: str
    description: str = ""
    format_string: Optional[str] = None
    folder: str = "Time Intelligence"


@dataclass
class DateDimension:
    """Represents a date dimension with hierarchies"""
    table_name: str
    date_column: str
    fiscal_config: FiscalYearConfig = field(default_factory=FiscalYearConfig)
    hierarchies: List[str] = field(default_factory=list)
    calculated_columns: List[Dict] = field(default_factory=list)


class CognosTimeIntelligenceConverter:
    """Converts Cognos time intelligence to Power BI DAX"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._load_cognos_time_functions()
    
    def _load_cognos_time_functions(self):
        """Load Cognos time function mappings"""
        self.cognos_time_mappings = {
            # Cognos Function -> DAX Template
            'current_date': 'TODAY()',
            'current_datetime': 'NOW()',
            'extract_year': 'YEAR({date_column})',
            'extract_month': 'MONTH({date_column})',
            'extract_quarter': 'QUARTER({date_column})',
            'extract_day': 'DAY({date_column})',
            'extract_weekday': 'WEEKDAY({date_column})',
            'extract_week': 'WEEKNUM({date_column})',
            
            # Cognos YTD functions
            'year_to_date': 'TOTALYTD({measure}, {date_table}[{date_column}])',
            'quarter_to_date': 'TOTALQTD({measure}, {date_table}[{date_column}])',
            'month_to_date': 'TOTALMTD({measure}, {date_table}[{date_column}])',
            
            # Cognos relative date functions
            'same_period_last_year': 'CALCULATE({measure}, SAMEPERIODLASTYEAR({date_table}[{date_column}]))',
            'previous_year': 'CALCULATE({measure}, PARALLELPERIOD({date_table}[{date_column}], -1, YEAR))',
            'previous_quarter': 'CALCULATE({measure}, PARALLELPERIOD({date_table}[{date_column}], -1, QUARTER))',
            'previous_month': 'CALCULATE({measure}, PARALLELPERIOD({date_table}[{date_column}], -1, MONTH))',
            
            # Cognos rolling calculations
            'rolling_average': 'AVERAGEX(DATESINPERIOD({date_table}[{date_column}], MAX({date_table}[{date_column}]), -{periods}, {period_type}), {measure})',
            'moving_total': 'CALCULATE({measure}, DATESINPERIOD({date_table}[{date_column}], MAX({date_table}[{date_column}]), -{periods}, {period_type}))'
        }
    
    def convert_cognos_time_function(self, cognos_function: str, parameters: Dict[str, Any]) -> str:
        """
        Convert Cognos time intelligence function to DAX
        
        Args:
            cognos_function: Name of the Cognos function
            parameters: Function parameters (measure, date_table, etc.)
            
        Returns:
            DAX expression
        """
        try:
            if cognos_function.lower() not in self.cognos_time_mappings:
                self.logger.warning(f"Unsupported Cognos time function: {cognos_function}")
                return cognos_function
            
            template = self.cognos_time_mappings[cognos_function.lower()]
            
            # Replace placeholders with actual values
            dax_expr = template.format(**parameters)
            
            self.logger.info(f"Converted Cognos time function: {cognos_function} -> {dax_expr}")
            return dax_expr
            
        except Exception as e:
            self.logger.error(f"Failed to convert time function {cognos_function}: {e}")
            return cognos_function
    
    def create_fiscal_year_calculations(self, date_dimension: DateDimension) -> List[Dict]:
        """Create fiscal year calculated columns"""
        calculations = []
        config = date_dimension.fiscal_config
        
        try:
            # Fiscal Year calculation
            if config.start_month != 1:
                fiscal_year_expr = f"""
                IF(
                    MONTH({date_dimension.table_name}[{date_dimension.date_column}]) >= {config.start_month},
                    YEAR({date_dimension.table_name}[{date_dimension.date_column}]) + {config.year_offset},
                    YEAR({date_dimension.table_name}[{date_dimension.date_column}]) + {config.year_offset - 1}
                )
                """
            else:
                fiscal_year_expr = f"YEAR({date_dimension.table_name}[{date_dimension.date_column}])"
            
            calculations.append({
                "name": "FiscalYear",
                "expression": fiscal_year_expr.strip(),
                "dataType": "int64",
                "isHidden": False,
                "summarizeBy": "none",
                "description": "Fiscal year based on company fiscal calendar"
            })
            
            # Fiscal Quarter calculation
            if config.start_month != 1:
                fiscal_quarter_expr = f"""
                SWITCH(
                    TRUE(),
                    MONTH({date_dimension.table_name}[{date_dimension.date_column}]) >= {config.start_month} && 
                    MONTH({date_dimension.table_name}[{date_dimension.date_column}]) <= {(config.start_month + 2) % 12 + 1}, "Q1",
                    MONTH({date_dimension.table_name}[{date_dimension.date_column}]) >= {(config.start_month + 3) % 12 + 1} && 
                    MONTH({date_dimension.table_name}[{date_dimension.date_column}]) <= {(config.start_month + 5) % 12 + 1}, "Q2",
                    MONTH({date_dimension.table_name}[{date_dimension.date_column}]) >= {(config.start_month + 6) % 12 + 1} && 
                    MONTH({date_dimension.table_name}[{date_dimension.date_column}]) <= {(config.start_month + 8) % 12 + 1}, "Q3",
                    "Q4"
                )
                """
            else:
                fiscal_quarter_expr = f'"Q" & QUARTER({date_dimension.table_name}[{date_dimension.date_column}])'
            
            calculations.append({
                "name": "FiscalQuarter",
                "expression": fiscal_quarter_expr.strip(),
                "dataType": "string",
                "isHidden": False,
                "summarizeBy": "none",
                "description": "Fiscal quarter based on company fiscal calendar"
            })
            
            # Fiscal Month calculation
            if config.start_month != 1:
                fiscal_month_expr = f"""
                MOD(MONTH({date_dimension.table_name}[{date_dimension.date_column}]) - {config.start_month} + 12, 12) + 1
                """
            else:
                fiscal_month_expr = f"MONTH({date_dimension.table_name}[{date_dimension.date_column}])"
            
            calculations.append({
                "name": "FiscalMonth",
                "expression": fiscal_month_expr.strip(),
                "dataType": "int64",
                "isHidden": False,
                "summarizeBy": "none",
                "description": "Fiscal month number based on company fiscal calendar"
            })
            
            # Period calculations
            calculations.extend([
                {
                    "name": "IsCurrentFiscalYear",
                    "expression": f"[FiscalYear] = IF(MONTH(TODAY()) >= {config.start_month}, YEAR(TODAY()) + {config.year_offset}, YEAR(TODAY()) + {config.year_offset - 1})",
                    "dataType": "boolean",
                    "isHidden": True,
                    "summarizeBy": "none",
                    "description": "Flag indicating if date is in current fiscal year"
                },
                {
                    "name": "DaysFromToday",
                    "expression": f"{date_dimension.table_name}[{date_dimension.date_column}] - TODAY()",
                    "dataType": "int64",
                    "isHidden": True,
                    "summarizeBy": "none",
                    "description": "Number of days from today (negative for past dates)"
                }
            ])
            
            self.logger.info(f"Created {len(calculations)} fiscal year calculations")
            return calculations
            
        except Exception as e:
            self.logger.error(f"Failed to create fiscal year calculations: {e}")
            return []
    
    def generate_time_intelligence_measures(self, base_measures: List[str], 
                                          date_dimension: DateDimension) -> List[TimeIntelligenceMeasure]:
        """Generate time intelligence measures for base measures"""
        time_measures = []
        
        for base_measure in base_measures:
            try:
                # Year to Date
                ytd_measure = TimeIntelligenceMeasure(
                    name=f"{base_measure} YTD",
                    base_measure=base_measure,
                    calculation_type=TimeIntelligenceType.YTD,
                    dax_expression=f"TOTALYTD([{base_measure}], {date_dimension.table_name}[{date_dimension.date_column}])",
                    description=f"Year to date total of {base_measure}",
                    format_string="#,##0.00"
                )
                time_measures.append(ytd_measure)
                
                # Quarter to Date
                qtd_measure = TimeIntelligenceMeasure(
                    name=f"{base_measure} QTD",
                    base_measure=base_measure,
                    calculation_type=TimeIntelligenceType.QTD,
                    dax_expression=f"TOTALQTD([{base_measure}], {date_dimension.table_name}[{date_dimension.date_column}])",
                    description=f"Quarter to date total of {base_measure}",
                    format_string="#,##0.00"
                )
                time_measures.append(qtd_measure)
                
                # Month to Date
                mtd_measure = TimeIntelligenceMeasure(
                    name=f"{base_measure} MTD",
                    base_measure=base_measure,
                    calculation_type=TimeIntelligenceType.MTD,
                    dax_expression=f"TOTALMTD([{base_measure}], {date_dimension.table_name}[{date_dimension.date_column}])",
                    description=f"Month to date total of {base_measure}",
                    format_string="#,##0.00"
                )
                time_measures.append(mtd_measure)
                
                # Same Period Last Year
                sply_measure = TimeIntelligenceMeasure(
                    name=f"{base_measure} SPLY",
                    base_measure=base_measure,
                    calculation_type=TimeIntelligenceType.SAME_PERIOD_LAST_YEAR,
                    dax_expression=f"CALCULATE([{base_measure}], SAMEPERIODLASTYEAR({date_dimension.table_name}[{date_dimension.date_column}]))",
                    description=f"Same period last year value of {base_measure}",
                    format_string="#,##0.00"
                )
                time_measures.append(sply_measure)
                
                # Year over Year Growth
                yoy_growth_measure = TimeIntelligenceMeasure(
                    name=f"{base_measure} YoY Growth %",
                    base_measure=base_measure,
                    calculation_type=TimeIntelligenceType.PERCENT_CHANGE,
                    dax_expression=f"DIVIDE([{base_measure}] - [{base_measure} SPLY], [{base_measure} SPLY], BLANK())",
                    description=f"Year over year growth percentage for {base_measure}",
                    format_string="0.00%"
                )
                time_measures.append(yoy_growth_measure)
                
                # Rolling 12 Month Average
                rolling_avg_measure = TimeIntelligenceMeasure(
                    name=f"{base_measure} Rolling 12M Avg",
                    base_measure=base_measure,
                    calculation_type=TimeIntelligenceType.ROLLING_AVERAGE,
                    dax_expression=f"AVERAGEX(DATESINPERIOD({date_dimension.table_name}[{date_dimension.date_column}], MAX({date_dimension.table_name}[{date_dimension.date_column}]), -12, MONTH), [{base_measure}])",
                    description=f"Rolling 12-month average of {base_measure}",
                    format_string="#,##0.00"
                )
                time_measures.append(rolling_avg_measure)
                
            except Exception as e:
                self.logger.error(f"Failed to create time intelligence measures for {base_measure}: {e}")
        
        self.logger.info(f"Generated {len(time_measures)} time intelligence measures")
        return time_measures
    
    def create_date_dimension_template(self, date_dimension: DateDimension) -> Dict[str, Any]:
        """Create a complete date dimension template with time intelligence"""
        try:
            # Base date calculations
            base_calculations = [
                {
                    "name": "Year",
                    "expression": f"YEAR({date_dimension.table_name}[{date_dimension.date_column}])",
                    "dataType": "int64",
                    "isHidden": False,
                    "summarizeBy": "none"
                },
                {
                    "name": "Quarter",
                    "expression": f'"Q" & QUARTER({date_dimension.table_name}[{date_dimension.date_column}])',
                    "dataType": "string",
                    "isHidden": False,
                    "summarizeBy": "none"
                },
                {
                    "name": "Month",
                    "expression": f"MONTH({date_dimension.table_name}[{date_dimension.date_column}])",
                    "dataType": "int64",
                    "isHidden": False,
                    "summarizeBy": "none"
                },
                {
                    "name": "MonthName",
                    "expression": f'FORMAT({date_dimension.table_name}[{date_dimension.date_column}], "MMM")',
                    "dataType": "string",
                    "isHidden": False,
                    "summarizeBy": "none"
                },
                {
                    "name": "Day",
                    "expression": f"DAY({date_dimension.table_name}[{date_dimension.date_column}])",
                    "dataType": "int64",
                    "isHidden": False,
                    "summarizeBy": "none"
                },
                {
                    "name": "DayOfWeek",
                    "expression": f"WEEKDAY({date_dimension.table_name}[{date_dimension.date_column}])",
                    "dataType": "int64",
                    "isHidden": False,
                    "summarizeBy": "none"
                },
                {
                    "name": "DayName",
                    "expression": f'FORMAT({date_dimension.table_name}[{date_dimension.date_column}], "ddd")',
                    "dataType": "string",
                    "isHidden": False,
                    "summarizeBy": "none"
                },
                {
                    "name": "WeekNumber",
                    "expression": f"WEEKNUM({date_dimension.table_name}[{date_dimension.date_column}])",
                    "dataType": "int64",
                    "isHidden": False,
                    "summarizeBy": "none"
                }
            ]
            
            # Add fiscal year calculations
            fiscal_calculations = self.create_fiscal_year_calculations(date_dimension)
            
            # Combine all calculations
            all_calculations = base_calculations + fiscal_calculations
            
            # Create hierarchies
            hierarchies = [
                {
                    "name": "Calendar",
                    "levels": [
                        {"name": "Year", "column": "Year", "ordinal": 0},
                        {"name": "Quarter", "column": "Quarter", "ordinal": 1},
                        {"name": "Month", "column": "MonthName", "ordinal": 2},
                        {"name": "Day", "column": date_dimension.date_column, "ordinal": 3}
                    ]
                },
                {
                    "name": "Fiscal",
                    "levels": [
                        {"name": "Fiscal Year", "column": "FiscalYear", "ordinal": 0},
                        {"name": "Fiscal Quarter", "column": "FiscalQuarter", "ordinal": 1},
                        {"name": "Fiscal Month", "column": "FiscalMonth", "ordinal": 2}
                    ]
                }
            ]
            
            date_template = {
                "table_name": date_dimension.table_name,
                "date_column": date_dimension.date_column,
                "calculated_columns": all_calculations,
                "hierarchies": hierarchies,
                "fiscal_config": {
                    "start_month": date_dimension.fiscal_config.start_month,
                    "fiscal_type": date_dimension.fiscal_config.fiscal_type.value
                }
            }
            
            self.logger.info(f"Created date dimension template with {len(all_calculations)} calculations and {len(hierarchies)} hierarchies")
            return date_template
            
        except Exception as e:
            self.logger.error(f"Failed to create date dimension template: {e}")
            return {}
    
    def convert_cognos_time_expression(self, cognos_expr: str, date_context: Dict[str, str]) -> str:
        """Convert complex Cognos time expressions to DAX"""
        try:
            # Common Cognos time expression patterns
            patterns = {
                # Extract year from date
                r'extract\s*\(\s*year\s*,\s*([^)]+)\s*\)': r'YEAR(\1)',
                r'_year\s*\(\s*([^)]+)\s*\)': r'YEAR(\1)',
                
                # Extract month from date
                r'extract\s*\(\s*month\s*,\s*([^)]+)\s*\)': r'MONTH(\1)',
                r'_month\s*\(\s*([^)]+)\s*\)': r'MONTH(\1)',
                
                # Extract quarter from date
                r'extract\s*\(\s*quarter\s*,\s*([^)]+)\s*\)': r'QUARTER(\1)',
                r'_quarter\s*\(\s*([^)]+)\s*\)': r'QUARTER(\1)',
                
                # Current date functions
                r'current_date\s*\(\s*\)': 'TODAY()',
                r'now\s*\(\s*\)': 'NOW()',
                
                # Date arithmetic
                r'([^+\-\s]+)\s*\+\s*(\d+)\s*days?': r'(\1 + \2)',
                r'([^+\-\s]+)\s*\-\s*(\d+)\s*days?': r'(\1 - \2)',
            }
            
            converted_expr = cognos_expr
            
            for pattern, replacement in patterns.items():
                converted_expr = re.sub(pattern, replacement, converted_expr, flags=re.IGNORECASE)
            
            self.logger.info(f"Converted time expression: '{cognos_expr}' -> '{converted_expr}'")
            return converted_expr
            
        except Exception as e:
            self.logger.error(f"Failed to convert time expression '{cognos_expr}': {e}")
            return cognos_expr


def create_standard_date_dimension(table_name: str = "Calendar", 
                                 date_column: str = "Date",
                                 fiscal_start_month: int = 1) -> DateDimension:
    """Create a standard date dimension configuration"""
    fiscal_config = FiscalYearConfig(
        start_month=fiscal_start_month,
        fiscal_type=FiscalPeriodType.STANDARD if fiscal_start_month == 1 else FiscalPeriodType.CUSTOM
    )
    
    return DateDimension(
        table_name=table_name,
        date_column=date_column,
        fiscal_config=fiscal_config
    )


def create_fiscal_date_dimension(table_name: str = "Calendar",
                                date_column: str = "Date", 
                                fiscal_type: FiscalPeriodType = FiscalPeriodType.APRIL_MARCH) -> DateDimension:
    """Create a fiscal year date dimension configuration"""
    fiscal_configs = {
        FiscalPeriodType.APRIL_MARCH: FiscalYearConfig(start_month=4, fiscal_type=fiscal_type),
        FiscalPeriodType.JULY_JUNE: FiscalYearConfig(start_month=7, fiscal_type=fiscal_type),
        FiscalPeriodType.OCTOBER_SEPTEMBER: FiscalYearConfig(start_month=10, fiscal_type=fiscal_type, year_offset=1)
    }
    
    fiscal_config = fiscal_configs.get(fiscal_type, FiscalYearConfig())
    
    return DateDimension(
        table_name=table_name,
        date_column=date_column,
        fiscal_config=fiscal_config
    )


# Demo usage
if __name__ == "__main__":
    # Create time intelligence converter
    converter = CognosTimeIntelligenceConverter()
    
    # Create a standard date dimension
    date_dim = create_standard_date_dimension("Calendar", "Date", fiscal_start_month=4)
    
    # Generate time intelligence measures
    base_measures = ["Sales Amount", "Quantity", "Profit"]
    time_measures = converter.generate_time_intelligence_measures(base_measures, date_dim)
    
    print(f"Generated {len(time_measures)} time intelligence measures:")
    for measure in time_measures[:5]:  # Show first 5
        print(f"  - {measure.name}: {measure.dax_expression}")
    
    # Create date dimension template
    date_template = converter.create_date_dimension_template(date_dim)
    print(f"\nDate dimension template created with {len(date_template.get('calculated_columns', []))} calculated columns")