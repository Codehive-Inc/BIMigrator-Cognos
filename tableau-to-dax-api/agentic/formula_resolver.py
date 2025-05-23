"""Agentic formula resolver for handling nested calculation references."""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from langchain.agents import AgentExecutor, Tool
from langchain.agents.format_scratchpad import format_log_to_str
from langchain.agents.output_parsers import ReActSingleInputOutputParser
from langchain.tools.render import render_text_description
from langchain.prompts import PromptTemplate
import json
from pathlib import Path

@dataclass
class CalculationNode:
    """Represents a calculation node with its dependencies."""
    table_name: str
    caption: str
    tableau_name: str
    formula: str
    dax_formula: str
    data_type: str
    is_measure: bool
    dependencies: List[str] = None

    def __post_init__(self):
        self.dependencies = self.dependencies or []

class FormulaResolver:
    """Agentic formula resolver that handles nested calculation references."""
    
    def __init__(self, calculations_data: Dict[str, Any] = None, calculations_path: str = None):
        self.calculations: Dict[str, CalculationNode] = {}
        if calculations_data:
            self.load_calculations_from_data(calculations_data)
        elif calculations_path:
            self.calculations_path = Path(calculations_path)
            self.load_calculations_from_file()
            
    def load_calculations_from_data(self, data: Dict[str, Any]):
        """Load calculations directly from a dictionary."""
        calcs = data.get("calculations", [])
        for calc in calcs:
            node = CalculationNode(
                table_name=calc["TableName"],
                caption=calc["FormulaCaptionTableau"],
                tableau_name=calc["TableauName"],
                formula=calc["FormulaTableau"],
                dax_formula=calc["FormulaDax"],
                data_type=calc["DataType"],
                is_measure=calc["IsMeasure"]
            )
            self.calculations[calc["TableauName"]] = node

    def load_calculations_from_file(self):
        """Load calculations from the JSON file."""
        if not self.calculations_path.exists():
            raise FileNotFoundError(f"Calculations file not found: {self.calculations_path}")
            
        with open(self.calculations_path) as f:
            data = json.load(f)
            self.load_calculations_from_data(data)

    def extract_dependencies(self, formula: str) -> List[str]:
        """Extract calculation dependencies from a formula."""
        import re
        # Look for [Calculation_*] patterns
        deps = re.findall(r'\[Calculation_\d+\]', formula)
        return list(set(deps))

    def resolve_calculation_chain(self, calc_name: str) -> List[CalculationNode]:
        """Resolve the calculation chain for a given calculation."""
        if calc_name not in self.calculations:
            raise KeyError(f"Calculation not found: {calc_name}")
            
        chain = []
        visited = set()
        
        def resolve_deps(name):
            if name in visited:
                return
            visited.add(name)
            node = self.calculations[name]
            deps = self.extract_dependencies(node.formula)
            node.dependencies = deps
            for dep in deps:
                if dep in self.calculations:
                    resolve_deps(dep)
            chain.append(node)
            
        resolve_deps(calc_name)
        return chain

    def get_calculation_by_name(self, name: str) -> Optional[CalculationNode]:
        """Get a calculation by its Tableau name."""
        return self.calculations.get(name)

class AgentTools:
    """Tools for the formula resolution agent."""
    
    def __init__(self, resolver: FormulaResolver):
        self.resolver = resolver
        
    def get_calculation_info(self, name: str) -> str:
        """Get information about a calculation."""
        calc = self.resolver.get_calculation_by_name(name)
        if not calc:
            return f"Calculation {name} not found"
        return f"Caption: {calc.caption}\nFormula: {calc.formula}\nDAX: {calc.dax_formula}"
        
    def get_dependencies(self, name: str) -> str:
        """Get dependencies for a calculation."""
        calc = self.resolver.get_calculation_by_name(name)
        if not calc:
            return f"Calculation {name} not found"
        deps = self.resolver.extract_dependencies(calc.formula)
        return f"Dependencies: {', '.join(deps) if deps else 'None'}"

class FormulaAgent:
    """Agent for resolving and transforming formulas."""
    
    def __init__(self, resolver: FormulaResolver):
        self.resolver = resolver
        self.tools = AgentTools(resolver)
        
    def resolve_formula(self, calc_name: str) -> Dict[str, Any]:
        """Resolve a formula and its dependencies."""
        # Get the calculation info
        calc_info = self.tools.get_calculation_info(calc_name)
        
        # Get dependencies
        deps_info = self.tools.get_dependencies(calc_name)
        
        # Get the full dependency chain
        chain = self.resolver.resolve_calculation_chain(calc_name)
        
        result = {
            "calculation": calc_info,
            "dependencies": deps_info,
            "chain": [
                {
                    "caption": node.caption,
                    "formula": node.formula,
                    "dax": node.dax_formula
                } for node in chain
            ]
        }
        
        return result
