"""
Mathematical utility functions for testing purposes.
"""

def calculate_fibonacci(n):
    """
    Calculate the nth Fibonacci number using iterative approach.
    
    Args:
        n (int): Position in Fibonacci sequence
        
    Returns:
        int: The nth Fibonacci number
    """
    if n <= 1:
        return n
    
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    
    return b


def factorial(n):
    """
    Calculate factorial of a number.
    
    Args:
        n (int): Number to calculate factorial for
        
    Returns:
        int: Factorial of n
    """
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers")
    if n == 0 or n == 1:
        return 1
    
    result = 1
    for i in range(2, n + 1):
        result *= i
    
    return result


def gcd(a, b):
    """
    Calculate Greatest Common Divisor using Euclidean algorithm.
    
    Args:
        a (int): First number
        b (int): Second number
        
    Returns:
        int: GCD of a and b
    """
    while b:
        a, b = b, a % b
    return a


def is_prime(n):
    """
    Check if a number is prime.
    
    Args:
        n (int): Number to check
        
    Returns:
        bool: True if n is prime, False otherwise
    """
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    
    for i in range(3, int(n**0.5) + 1, 2):
        if n % i == 0:
            return False
    
    return True 