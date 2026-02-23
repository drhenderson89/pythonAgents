"""Tool for calculating mathematical expressions."""

from langchain_core.tools import tool
from calculator.pkg.calculator import Calculator

# Initialize calculator
calc = Calculator()


@tool
def calculate_expression(expression: str) -> str:
    """
    Evaluate a mathematical expression using the calculator.
    Supports +, -, *, / operators, parentheses/brackets, and negative numbers.

    Args:
        expression: The mathematical expression to evaluate (e.g., "10 + 5 * 2", "(3+5)*2", "-5 + 3")

    Returns:
        The result of the calculation or an error message.
    """
    try:
        result = calc.evaluate(expression)
        if result is None:
            return "Error: Empty expression provided."
        return f"Result: {result}"
    except Exception as e:
        return f"Error calculating expression '{expression}': {str(e)}"
