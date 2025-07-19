"""
String processing utilities for text manipulation.
"""

def reverse_string(text):
    """
    Reverse a string.
    
    Args:
        text (str): Input string
        
    Returns:
        str: Reversed string
    """
    return text[::-1]


def count_words(text):
    """
    Count the number of words in a text.
    
    Args:
        text (str): Input text
        
    Returns:
        int: Number of words
    """
    return len(text.split())


def capitalize_words(text):
    """
    Capitalize the first letter of each word.
    
    Args:
        text (str): Input text
        
    Returns:
        str: Text with capitalized words
    """
    return ' '.join(word.capitalize() for word in text.split())


def remove_duplicates(text):
    """
    Remove duplicate characters from a string while preserving order.
    
    Args:
        text (str): Input string
        
    Returns:
        str: String with duplicates removed
    """
    seen = set()
    result = []
    
    for char in text:
        if char not in seen:
            seen.add(char)
            result.append(char)
    
    return ''.join(result)


def is_palindrome(text):
    """
    Check if a string is a palindrome (ignoring case and spaces).
    
    Args:
        text (str): Input string
        
    Returns:
        bool: True if palindrome, False otherwise
    """
    cleaned = text.replace(' ', '').lower()
    return cleaned == cleaned[::-1]


class TextAnalyzer:
    """
    A class for analyzing text content.
    """
    
    def __init__(self, text):
        """
        Initialize with text to analyze.
        
        Args:
            text (str): Text to analyze
        """
        self.text = text
        self.word_count = count_words(text)
        self.char_count = len(text)
    
    def get_stats(self):
        """
        Get basic statistics about the text.
        
        Returns:
            dict: Dictionary with text statistics
        """
        return {
            'character_count': self.char_count,
            'word_count': self.word_count,
            'sentence_count': self.text.count('.') + self.text.count('!') + self.text.count('?'),
            'paragraph_count': self.text.count('\n\n') + 1,
            'is_palindrome': is_palindrome(self.text)
        }
    
    def find_longest_word(self):
        """
        Find the longest word in the text.
        
        Returns:
            str: The longest word
        """
        words = self.text.split()
        return max(words, key=len) if words else "" 