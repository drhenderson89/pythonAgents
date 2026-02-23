# calculator.py

class Calculator:
    def __init__(self):
        self.operators = {
            "+": lambda a, b: a + b,
            "-": lambda a, b: a - b,
            "*": lambda a, b: a * b,
            "/": lambda a, b: a / b,
        }

        self.precedence = {
            "+": 1,
            "-": 1,
            "*": 2,
            "/": 2,
        }

    def evaluate(self, expression):
        if not expression or expression.isspace():
            return None
        tokens = self._tokenize(expression)
        return self._evaluate_infix(tokens)

    def _tokenize(self, expression):
        """Tokenize expression with or without spaces, handling brackets and operators."""
        tokens = []
        current_number = []

        for i, char in enumerate(expression):
            if char.isdigit() or char == '.':
                current_number.append(char)
            elif char == '-':
                # If we're currently building a number, minus must be subtraction
                if current_number:
                    tokens.append(''.join(current_number))
                    current_number = []
                    tokens.append(char)
                else:
                    # Check if minus is part of a negative number or unary negation
                    next_is_digit = (i + 1 < len(expression) and
                                     (expression[i + 1].isdigit() or expression[i + 1] == '.'))
                    is_unary = (
                        i == 0 or
                        expression[i-1] in '([{' or
                        (tokens and tokens[-1] in self.operators)
                    )

                    if is_unary and next_is_digit:
                        # Negative number: -5, (-3), 10*-2
                        current_number.append(char)
                    elif is_unary and not next_is_digit:
                        # Unary minus before bracket: -(5+3) becomes 0-(5+3)
                        tokens.append('0')
                        tokens.append(char)
                    else:
                        # Subtraction operator
                        tokens.append(char)
            elif char in self.operators or char in '()[]{}':
                if current_number:
                    tokens.append(''.join(current_number))
                    current_number = []
                if char in '()[]{}':
                    # Normalize all bracket types to parentheses
                    tokens.append('(' if char in '([{' else ')')
                else:
                    tokens.append(char)
            elif char.isspace():
                if current_number:
                    tokens.append(''.join(current_number))
                    current_number = []
            else:
                raise ValueError(f"invalid character: {char}")

        if current_number:
            tokens.append(''.join(current_number))

        return tokens

    def _evaluate_infix(self, tokens):
        values = []
        operators = []

        for token in tokens:
            if token == '(':
                operators.append(token)
            elif token == ')':
                # Process all operators until we find the matching '('
                while operators and operators[-1] != '(':
                    self._apply_operator(operators, values)
                if not operators:
                    raise ValueError("mismatched parentheses")
                operators.pop()  # Remove the '('
            elif token in self.operators:
                while (
                    operators
                    and operators[-1] != '('
                    and operators[-1] in self.operators
                    and self.precedence[operators[-1]] >= self.precedence[token]
                ):
                    self._apply_operator(operators, values)
                operators.append(token)
            else:
                try:
                    values.append(float(token))
                except ValueError:
                    raise ValueError(f"invalid token: {token}")

        while operators:
            if operators[-1] == '(':
                raise ValueError("mismatched parentheses")
            self._apply_operator(operators, values)

        if len(values) != 1:
            raise ValueError("invalid expression")

        return values[0]

    def _apply_operator(self, operators, values):
        if not operators:
            return

        operator = operators.pop()
        if len(values) < 2:
            raise ValueError(f"not enough operands for operator {operator}")

        b = values.pop()
        a = values.pop()
        values.append(self.operators[operator](a, b))
