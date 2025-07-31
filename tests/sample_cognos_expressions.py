"""
Real Cognos expression samples for testing validation framework

This module contains actual Cognos expressions collected from real-world reports
to test the validation and conversion capabilities.
"""

# Sample Cognos expressions from real reports
COGNOS_EXPRESSIONS = {
    "simple_aggregations": [
        "total([Sales Amount])",
        "sum([Revenue])",
        "count([Customer ID])",
        "average([Order Value])",
        "maximum([Price])",
        "minimum([Discount])"
    ],
    
    "conditional_aggregations": [
        "total([Sales Amount] for [Region] = 'North America')",
        "sum([Revenue] for [Product Category] = 'Electronics')",
        "count([Customer ID] for [Status] = 'Active')",
        "average([Order Value] for [Year] = 2023)",
        "total([Quantity] for [Country] in ('USA', 'Canada'))",
        "sum([Sales Amount] for [Date] between '2023-01-01' and '2023-12-31')"
    ],
    
    "arithmetic_expressions": [
        "[Quantity] * [Unit Price]",
        "[Revenue] - [Cost]",
        "[Sales Amount] / [Units Sold]",
        "([Revenue] - [Cost]) / [Revenue] * 100",
        "[Current Year Sales] - [Previous Year Sales]",
        "([Actual] - [Budget]) / [Budget]"
    ],
    
    "case_when_expressions": [
        "case when [Status] = 'Active' then 1 else 0 end",
        "case when [Revenue] > 10000 then 'High' when [Revenue] > 5000 then 'Medium' else 'Low' end",
        "case when [Region] = 'North America' then [Sales Amount] * 1.1 else [Sales Amount] end",
        "case when [Product Category] is null then 'Unknown' else [Product Category] end",
        "case when [Order Date] >= current_date - 30 then 'Recent' else 'Old' end"
    ],
    
    "date_functions": [
        "extract(year, [Order Date])",
        "extract(month, [Sale Date])",
        "extract(day, [Transaction Date])",
        "_first_of_month([Order Date])",
        "_last_of_month([Sale Date])",
        "current_date",
        "[Order Date] + interval '30' day(2)"
    ],
    
    "string_functions": [
        "trim([Customer Name])",
        "upper([Product Name])",
        "lower([Category])",
        "substring([Product Code], 1, 3)",
        "length([Description])",
        "position('Electronics' in [Category])",
        "[First Name] || ' ' || [Last Name]"
    ],
    
    "complex_calculations": [
        "running-total([Sales Amount] for [Order Date])",
        "rank([Sales Amount] for [Region])",
        "percentile([Revenue], 90 for [Product Category])",
        "moving-average([Sales Amount], 3 for [Month])",
        "lag([Sales Amount], 1 for [Date] asc)",
        "ntile([Revenue], 4 for [Customer ID])"
    ],
    
    "nested_expressions": [
        "total(case when [Status] = 'Completed' then [Amount] else 0 end)",
        "sum([Quantity] * case when [Discount] > 0 then [Unit Price] * (1 - [Discount]) else [Unit Price] end)",
        "count(case when extract(year, [Order Date]) = extract(year, current_date) then [Order ID] else null end)",
        "average(case when [Category] = 'Premium' then [Price] else null end)",
        "total([Revenue] for case when [Region] in ('US', 'CA') then 'North America' else 'Other' end = 'North America')"
    ],
    
    "problematic_expressions": [
        # These are known to cause issues in conversion
        "total([Sales] for [Region] = )",  # Incomplete filter
        "sum([Revenue] +)",  # Incomplete arithmetic
        "case when [Status] then 'Active' end",  # Missing else clause
        "total([Amount] for [Date] between)",  # Incomplete between clause
        "rank([Sales] for)",  # Missing grouping
        "substring([Code], )",  # Missing parameters
        "[Field1] || || [Field2]",  # Double concatenation operator
        "extract(invalid_part, [Date])",  # Invalid date part
        "percentile([Revenue], 150 for [Category])",  # Invalid percentile value
        "moving-average([Sales], -1 for [Date])"  # Invalid window size
    ]
}

# Expected DAX conversions for validation
EXPECTED_DAX_CONVERSIONS = {
    "total([Sales Amount])": "SUM(Sales[Amount])",
    "sum([Revenue])": "SUM(Sales[Revenue])",
    "count([Customer ID])": "COUNT(Customer[ID])",
    "average([Order Value])": "AVERAGE(Orders[Value])",
    "maximum([Price])": "MAX(Product[Price])",
    "minimum([Discount])": "MIN(Sales[Discount])",
    
    "total([Sales Amount] for [Region] = 'North America')": 
        "CALCULATE(SUM(Sales[Amount]), Region[Name] = \"North America\")",
    
    "[Quantity] * [Unit Price]": 
        "Sales[Quantity] * Sales[UnitPrice]",
    
    "case when [Status] = 'Active' then 1 else 0 end":
        "IF(Customer[Status] = \"Active\", 1, 0)",
    
    "extract(year, [Order Date])":
        "YEAR(Orders[OrderDate])"
}

# Sample M-Query patterns
MQUERY_PATTERNS = {
    "simple_sql_source": '''
    let
        Source = Sql.Database("server", "database", [Query="SELECT * FROM Sales"])
    in
        Source
    ''',
    
    "filtered_sql_source": '''
    let
        Source = Sql.Database("server", "database", [Query="SELECT * FROM Sales WHERE Region = 'US'"]),
        Navigation = Source{[Name="Query1"]}[Data]
    in
        Navigation
    ''',
    
    "complex_sql_with_joins": '''
    let
        Source = Sql.Database("server", "database", [Query="
            SELECT s.*, c.CustomerName, p.ProductName 
            FROM Sales s 
            JOIN Customer c ON s.CustomerID = c.ID 
            JOIN Product p ON s.ProductID = p.ID
        "]),
        Navigation = Source{[Name="Query1"]}[Data]
    in
        Navigation
    ''',
    
    "select_star_fallback": '''
    let
        Source = Sql.Database("server", "database", [Query="SELECT * FROM Sales"])
    in
        Source
    '''
}

# Sample validation test cases
VALIDATION_TEST_CASES = {
    "valid_cognos": {
        "expressions": COGNOS_EXPRESSIONS["simple_aggregations"] + 
                      COGNOS_EXPRESSIONS["arithmetic_expressions"][:3],
        "expected_valid": True
    },
    
    "invalid_cognos": {
        "expressions": COGNOS_EXPRESSIONS["problematic_expressions"],
        "expected_valid": False
    },
    
    "complex_cognos": {
        "expressions": COGNOS_EXPRESSIONS["complex_calculations"] + 
                      COGNOS_EXPRESSIONS["nested_expressions"],
        "expected_complexity": "high"
    }
}

# Performance test datasets
PERFORMANCE_TEST_DATA = {
    "small_dataset": {
        "expressions": COGNOS_EXPRESSIONS["simple_aggregations"],
        "expected_time_per_expr": 0.1  # seconds
    },
    
    "medium_dataset": {
        "expressions": sum([
            COGNOS_EXPRESSIONS["simple_aggregations"],
            COGNOS_EXPRESSIONS["conditional_aggregations"],
            COGNOS_EXPRESSIONS["arithmetic_expressions"]
        ], []),
        "expected_time_per_expr": 0.2
    },
    
    "large_dataset": {
        "expressions": sum(COGNOS_EXPRESSIONS.values(), []),
        "expected_time_per_expr": 0.3
    }
}

# Real-world report structures for integration testing
SAMPLE_REPORT_STRUCTURES = {
    "sales_report": {
        "name": "Monthly Sales Report",
        "data_items": [
            {"name": "Sales Amount", "type": "measure"},
            {"name": "Customer ID", "type": "dimension"},
            {"name": "Product Name", "type": "dimension"},
            {"name": "Order Date", "type": "dimension"},
            {"name": "Region", "type": "dimension"}
        ],
        "calculations": [
            "total([Sales Amount])",
            "total([Sales Amount] for [Region] = 'US')",
            "([Sales Amount] - lag([Sales Amount], 1 for [Order Date] asc))",
            "rank([Sales Amount] for [Region])"
        ]
    },
    
    "financial_report": {
        "name": "Financial Performance Dashboard",
        "data_items": [
            {"name": "Revenue", "type": "measure"},
            {"name": "Cost", "type": "measure"},
            {"name": "Profit", "type": "measure"},
            {"name": "Account", "type": "dimension"},
            {"name": "Period", "type": "dimension"}
        ],
        "calculations": [
            "[Revenue] - [Cost]",
            "([Revenue] - [Cost]) / [Revenue] * 100",
            "case when [Profit] > 0 then 'Profitable' else 'Loss' end",
            "moving-average([Revenue], 3 for [Period])"
        ]
    },
    
    "customer_report": {
        "name": "Customer Analysis Report",
        "data_items": [
            {"name": "Customer Name", "type": "dimension"},
            {"name": "Order Value", "type": "measure"},
            {"name": "Order Count", "type": "measure"},
            {"name": "Last Order Date", "type": "dimension"},
            {"name": "Status", "type": "dimension"}
        ],
        "calculations": [
            "count([Customer Name])",
            "average([Order Value])",
            "case when [Last Order Date] >= current_date - 90 then 'Active' else 'Inactive' end",
            "total([Order Value] for [Status] = 'Premium')"
        ]
    }
}


def get_expression_samples(category: str) -> list:
    """Get expression samples by category
    
    Args:
        category: Category name from COGNOS_EXPRESSIONS
        
    Returns:
        List of expressions in the specified category
    """
    return COGNOS_EXPRESSIONS.get(category, [])


def get_all_expressions() -> list:
    """Get all expression samples
    
    Returns:
        List of all expressions across all categories
    """
    return sum(COGNOS_EXPRESSIONS.values(), [])


def get_test_cases(test_type: str) -> dict:
    """Get test cases by type
    
    Args:
        test_type: Type of test cases to retrieve
        
    Returns:
        Dictionary containing test case data
    """
    return VALIDATION_TEST_CASES.get(test_type, {})


def get_performance_data(dataset_size: str) -> dict:
    """Get performance test data by dataset size
    
    Args:
        dataset_size: Size of dataset ('small', 'medium', 'large')
        
    Returns:
        Dictionary containing performance test data
    """
    return PERFORMANCE_TEST_DATA.get(dataset_size, {})


def get_sample_report(report_name: str) -> dict:
    """Get sample report structure by name
    
    Args:
        report_name: Name of the sample report
        
    Returns:
        Dictionary containing report structure
    """
    return SAMPLE_REPORT_STRUCTURES.get(report_name, {})