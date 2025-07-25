# Modified at 23:10:19
"""
calculator.py

Generated from prompt: Create a new Python file named calculator.py with an empty template for a calculator class.

Created at: 2025-07-25 23:10:19

"""


class Calculator:
    """Calculator class template."""
    
    def __init__(self):
        pass
    
    def add(self, a, b):
        """Add two numbers."""
        return a + b
    
    def subtract(self, a, b):
        """Subtract b from a."""
        return a - b
    
    def multiply(self, a, b):
        """Multiply two numbers."""
        return a * b
    
    def divide(self, a, b):
        """Divide a by b."""
        if b == 0:
            raise ValueError('Cannot divide by zero')
        return a / b
