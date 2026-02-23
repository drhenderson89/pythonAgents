# tests.py

import unittest
from pkg.calculator import Calculator


class TestCalculator(unittest.TestCase):
    def setUp(self):
        self.calculator = Calculator()

    # Basic operations with spaces
    def test_addition(self):
        result = self.calculator.evaluate("3 + 5")
        self.assertEqual(result, 8)

    def test_subtraction(self):
        result = self.calculator.evaluate("10 - 4")
        self.assertEqual(result, 6)

    def test_multiplication(self):
        result = self.calculator.evaluate("3 * 4")
        self.assertEqual(result, 12)

    def test_division(self):
        result = self.calculator.evaluate("10 / 2")
        self.assertEqual(result, 5)

    # Basic operations without spaces
    def test_addition_no_spaces(self):
        result = self.calculator.evaluate("3+5")
        self.assertEqual(result, 8)

    def test_subtraction_no_spaces(self):
        result = self.calculator.evaluate("10-4")
        self.assertEqual(result, 6)

    def test_multiplication_no_spaces(self):
        result = self.calculator.evaluate("3*4")
        self.assertEqual(result, 12)

    def test_division_no_spaces(self):
        result = self.calculator.evaluate("10/2")
        self.assertEqual(result, 5)

    # Mixed spacing
    def test_mixed_spaces(self):
        result = self.calculator.evaluate("3+ 5 *2")
        self.assertEqual(result, 13)

    # Operator precedence
    def test_precedence_multiply_before_add(self):
        result = self.calculator.evaluate("3 + 5 * 2")
        self.assertEqual(result, 13)

    def test_precedence_divide_before_subtract(self):
        result = self.calculator.evaluate("10 - 8 / 2")
        self.assertEqual(result, 6)

    def test_precedence_left_to_right_same_level(self):
        result = self.calculator.evaluate("10 - 3 - 2")
        self.assertEqual(result, 5)

    def test_nested_expression(self):
        result = self.calculator.evaluate("3 * 4 + 5")
        self.assertEqual(result, 17)

    def test_complex_expression(self):
        result = self.calculator.evaluate("2 * 3 - 8 / 2 + 5")
        self.assertEqual(result, 7)

    # Parentheses - basic
    def test_parentheses_basic(self):
        result = self.calculator.evaluate("(3 + 5)")
        self.assertEqual(result, 8)

    def test_parentheses_change_precedence(self):
        result = self.calculator.evaluate("(3 + 5) * 2")
        self.assertEqual(result, 16)

    def test_parentheses_override_precedence(self):
        result = self.calculator.evaluate("2 * (3 + 5)")
        self.assertEqual(result, 16)

    def test_parentheses_no_spaces(self):
        result = self.calculator.evaluate("(3+5)*2")
        self.assertEqual(result, 16)

    # Nested parentheses
    def test_nested_parentheses(self):
        result = self.calculator.evaluate("((3 + 5) * 2)")
        self.assertEqual(result, 16)

    def test_deeply_nested_parentheses(self):
        result = self.calculator.evaluate("((2 + 3) * (4 + 1))")
        self.assertEqual(result, 25)

    def test_multiple_nested_levels(self):
        result = self.calculator.evaluate("(2 + (3 * (4 + 5)))")
        self.assertEqual(result, 29)

    # Square and curly brackets
    def test_square_brackets(self):
        result = self.calculator.evaluate("[3 + 5] * 2")
        self.assertEqual(result, 16)

    def test_curly_brackets(self):
        result = self.calculator.evaluate("{3 + 5} * 2")
        self.assertEqual(result, 16)

    def test_mixed_bracket_types(self):
        result = self.calculator.evaluate("[(3 + 5) * {2 + 1}]")
        self.assertEqual(result, 24)

    # Negative numbers - basic
    def test_negative_number_at_start(self):
        result = self.calculator.evaluate("-5 + 3")
        self.assertEqual(result, -2)

    def test_negative_number_single(self):
        result = self.calculator.evaluate("-5")
        self.assertEqual(result, -5)

    def test_negative_number_after_operator(self):
        result = self.calculator.evaluate("10 + -5")
        self.assertEqual(result, 5)

    def test_negative_number_after_multiply(self):
        result = self.calculator.evaluate("10 * -5")
        self.assertEqual(result, -50)

    def test_negative_number_after_divide(self):
        result = self.calculator.evaluate("10 / -5")
        self.assertEqual(result, -2)

    def test_negative_number_no_spaces(self):
        result = self.calculator.evaluate("10+-5")
        self.assertEqual(result, 5)

    # Multiple negative numbers
    def test_two_negative_numbers(self):
        result = self.calculator.evaluate("-5 + -3")
        self.assertEqual(result, -8)

    def test_negative_subtract_negative(self):
        result = self.calculator.evaluate("-5 - -3")
        self.assertEqual(result, -2)

    def test_negative_multiply_negative(self):
        result = self.calculator.evaluate("-5 * -3")
        self.assertEqual(result, 15)

    def test_negative_divide_negative(self):
        result = self.calculator.evaluate("-10 / -5")
        self.assertEqual(result, 2)

    # Negative numbers with parentheses
    def test_negative_in_parentheses(self):
        result = self.calculator.evaluate("(-5) + 3")
        self.assertEqual(result, -2)

    def test_negative_parentheses_multiply(self):
        result = self.calculator.evaluate("(-5) * 2")
        self.assertEqual(result, -10)

    def test_negative_expression_in_parentheses(self):
        result = self.calculator.evaluate("-(5 + 3)")
        self.assertEqual(result, -8)

    def test_negative_complex_expression(self):
        result = self.calculator.evaluate("-(5 + 3) * 2")
        self.assertEqual(result, -16)

    def test_negative_expression_with_multiply(self):
        result = self.calculator.evaluate("10 + -(5 * 2)")
        self.assertEqual(result, 0)

    def test_double_negative_parentheses(self):
        result = self.calculator.evaluate("-(-5)")
        self.assertEqual(result, 5)

    def test_negative_nested_expression(self):
        result = self.calculator.evaluate("-(3 + (5 * 2))")
        self.assertEqual(result, -13)

    # Complex combinations
    def test_all_operators_with_negatives(self):
        result = self.calculator.evaluate("-5 + 3 * -2 - 10 / -5")
        self.assertEqual(result, -9)

    def test_complex_with_parentheses_and_negatives(self):
        result = self.calculator.evaluate("(-5 + 3) * (10 - -2)")
        self.assertEqual(result, -24)

    def test_nested_negatives_with_brackets(self):
        result = self.calculator.evaluate("-(-(5 + 3) * 2)")
        self.assertEqual(result, 16)

    def test_multiple_operations_mixed_spacing(self):
        result = self.calculator.evaluate("10+5* 2-(8/2)")
        self.assertEqual(result, 16)

    def test_all_bracket_types_with_negatives(self):
        result = self.calculator.evaluate("-[{3 + 5} * (2 + -1)]")
        self.assertEqual(result, -8)

    # Decimal numbers
    def test_decimal_addition(self):
        result = self.calculator.evaluate("3.5 + 2.5")
        self.assertEqual(result, 6.0)

    def test_negative_decimal(self):
        result = self.calculator.evaluate("-3.5 + 2.5")
        self.assertEqual(result, -1.0)

    def test_decimal_in_complex_expression(self):
        result = self.calculator.evaluate("(10.5 + -2.5) * 2")
        self.assertEqual(result, 16.0)

    # Edge cases
    def test_empty_expression(self):
        result = self.calculator.evaluate("")
        self.assertIsNone(result)

    def test_whitespace_only(self):
        result = self.calculator.evaluate("   ")
        self.assertIsNone(result)

    def test_single_number(self):
        result = self.calculator.evaluate("42")
        self.assertEqual(result, 42)

    def test_zero_operations(self):
        result = self.calculator.evaluate("0 + 0")
        self.assertEqual(result, 0)

    def test_division_by_negative(self):
        result = self.calculator.evaluate("10 / -2")
        self.assertEqual(result, -5)

    # Error cases
    def test_invalid_operator(self):
        with self.assertRaises(ValueError):
            self.calculator.evaluate("$ 3 5")

    def test_invalid_character(self):
        with self.assertRaises(ValueError):
            self.calculator.evaluate("3 + 5 & 2")

    def test_mismatched_parentheses_open(self):
        with self.assertRaises(ValueError):
            self.calculator.evaluate("(3 + 5")

    def test_mismatched_parentheses_close(self):
        with self.assertRaises(ValueError):
            self.calculator.evaluate("3 + 5)")

    def test_empty_parentheses(self):
        with self.assertRaises(ValueError):
            self.calculator.evaluate("()")

    def test_not_enough_operands(self):
        with self.assertRaises(ValueError):
            self.calculator.evaluate("+ 3")


if __name__ == "__main__":
    unittest.main()
