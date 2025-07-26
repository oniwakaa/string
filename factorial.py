```python
def factorial(n: int) -> int:
    """
    Calculate the factorial of a non-negative integer.

    The factorial of a non-negative integer n, denoted by n!, is the product of all positive integers less than or equal to n.
    For example:
    factorial(0) == 1
    factorial(1) == 1
    factorial(5) == 120
    factorial(10) == 3628800

    Args:
        n (int): The non-negative integer for which to calculate the factorial.

    Returns:
        int: The factorial of n.

    Raises:
        TypeError: if n is not an integer.
        ValueError: if n is a negative integer.
    """
    if not isinstance(n, int):
        raise TypeError("Input must be an integer.")
    if n < 0:
        raise ValueError("Input must be a non-negative integer.")

    if n == 0:
        return 1  # Base case: factorial of 0 is 1
    else:
        result = 1
        for i in range(1, n + 1):
            result *= i
        return result


if __name__ == '__main__':
    # Example Usage
    print(f"Factorial of 0: {factorial(0)}")
    print(f"Factorial of 1: {factorial(1)}")
    print(f"Factorial of 5: {factorial(5)}")
    print(f"Factorial of 10: {factorial(10)}")

    # Example of error handling
    try:
        print(f"Factorial of -1: {factorial(-1)}")
    except ValueError as e:
        print(f"Error: {e}")

    try:
        print(f"Factorial of 3.14: {factorial(3.14)}")
    except TypeError as e:
        print(f"Error: {e}")
```