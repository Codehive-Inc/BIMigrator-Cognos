"""Main entry point for the agentic formula resolver."""
import argparse
from pathlib import Path
from formula_resolver import FormulaResolver, FormulaAgent

def main():
    parser = argparse.ArgumentParser(description='Resolve Tableau calculation formulas and dependencies')
    parser.add_argument('calculations_file', help='Path to the calculations.json file')
    parser.add_argument('calculation_name', help='Name of the calculation to resolve')
    args = parser.parse_args()
    
    # Initialize the resolver and agent
    resolver = FormulaResolver(args.calculations_file)
    agent = FormulaAgent(resolver)
    
    # Resolve the formula
    try:
        result = agent.resolve_formula(args.calculation_name)
        print("\nAgent Resolution Result:")
        print(result)
        
        print("\nCalculation Chain:")
        chain = resolver.resolve_calculation_chain(args.calculation_name)
        for node in chain:
            print(f"\n{node.caption} ({node.tableau_name}):")
            print(f"Formula: {node.formula}")
            print(f"Dependencies: {node.dependencies}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
