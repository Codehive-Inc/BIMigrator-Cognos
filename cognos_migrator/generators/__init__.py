"""
Power BI project file generators package
"""

# WARNING: This import structure causes the wrong PowerBIProjectGenerator to be used
# The version in .generators does NOT have LLM integration
# The version in ..generators DOES have LLM integration
from .generators import PowerBIProjectGenerator, TemplateEngine, DocumentationGenerator

# TODO: Refactor the codebase to eliminate duplicate PowerBIProjectGenerator classes
# and ensure the LLM-integrated version is always used
