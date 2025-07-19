# Test Codebase

This is a sample codebase for testing the MemOS code loading functionality.

## Files

### math_utils.py
Contains mathematical utility functions:
- `calculate_fibonacci(n)` - Calculates Fibonacci numbers
- `factorial(n)` - Calculates factorial
- `gcd(a, b)` - Finds greatest common divisor
- `is_prime(n)` - Checks if a number is prime

### string_processor.py
Contains string processing utilities:
- `reverse_string(text)` - Reverses a string
- `count_words(text)` - Counts words in text
- `capitalize_words(text)` - Capitalizes words
- `remove_duplicates(text)` - Removes duplicate characters
- `is_palindrome(text)` - Checks if text is palindrome
- `TextAnalyzer` class - Analyzes text content

## Usage

These modules provide utility functions for mathematical operations and string processing.
The code is designed to test the MemOS codebase loading and retrieval functionality.

## Testing

You can test these functions by importing them:

```python
from math_utils import calculate_fibonacci, factorial
from string_processor import TextAnalyzer

# Calculate 10th Fibonacci number
fib_10 = calculate_fibonacci(10)

# Analyze some text
analyzer = TextAnalyzer("Hello world this is a test")
stats = analyzer.get_stats()
``` 