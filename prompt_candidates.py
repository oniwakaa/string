#!/usr/bin/env python3
"""
Minimal prompt candidates for Gemma3n intent classification testing.
Testing focused, concise prompts to improve classification reliability.
"""

# Current verbose prompt (195+ tokens)
CURRENT_PROMPT = """You are an expert intent classifier for an AI coding assistant. Analyze the user's prompt and classify it into the most appropriate intent category.

Available intents:
{intents}

Instructions:
1. Identify the PRIMARY intent - the main action the user wants to perform
2. Identify any SECONDARY intents that might also apply
3. Provide a confidence score (0.0-1.0) for your classification
4. Detect any context modifiers (e.g., "based on existing code", "in the project")

Respond in JSON format:
{{
    "primary_intent": "intent_name",
    "confidence": 0.85,
    "secondary_intents": ["intent1", "intent2"],
    "context_modifiers": ["requires_context", "has_file_reference"],
    "reasoning": "Brief explanation of classification"
}}

User prompt: "{prompt}"

Classification:"""

# Candidate 1: Ultra-minimal (15 tokens)
CANDIDATE_1 = """Classify: {prompt}

Options: {intent_list}

Answer:"""

# Candidate 2: Simple structured (25 tokens)
CANDIDATE_2 = """Intent classification for: {prompt}

Categories: {intent_list}

Choose the best match:"""

# Candidate 3: Direct command (20 tokens)
CANDIDATE_3 = """User request: {prompt}

Select intent from: {intent_list}

Intent:"""

# Test prompts covering different intent categories
TEST_PROMPTS = [
    # Web research intents
    "scrape data from https://example.com",
    "fetch the content of this website",
    "extract information from the webpage",
    
    # Codebase query intents
    "find the implementation of the login function",
    "where is the database connection class?",
    "explain how the authentication works",
    
    # Code generation intents
    "create a REST API endpoint for user management",
    "generate a Python function to validate emails",
    "build a React component for data visualization",
    
    # Code editing intents
    "fix the bug in the authentication function",
    "refactor this method to improve performance",
    "update the error handling in this code",
    
    # Code analysis intents
    "analyze this code for potential issues",
    "review the security of this implementation",
    "audit the performance bottlenecks",
    
    # Documentation intents
    "document this API endpoint",
    "create usage examples for this class",
    "explain how to use this module",
    
    # Mixed/complex prompts
    "find the user authentication code and fix any security issues",
    "scrape the Python documentation and generate example code",
    "analyze my database queries and create performance docs",
    
    # Edge cases
    "hello",
    "what can you do?",
    "help me with my project",
    "I need assistance",
    "this doesn't work",
    
    # Ambiguous prompts
    "show me the code",
    "make it better",
    "fix this",
    "what's wrong here?",
    "improve the performance",
    
    # File/context specific
    "edit main.py to add error handling",
    "analyze the security in auth.py",
    "generate docs for the API module"
]

# Available intents (simplified list)
INTENT_OPTIONS = [
    "web_research",
    "codebase_query", 
    "code_generation",
    "code_editing",
    "code_analysis",
    "documentation",
    "general_query"
]

if __name__ == "__main__":
    print(f"Current prompt length: {len(CURRENT_PROMPT.split())} tokens")
    print(f"Candidate 1 length: {len(CANDIDATE_1.split())} tokens")
    print(f"Candidate 2 length: {len(CANDIDATE_2.split())} tokens") 
    print(f"Candidate 3 length: {len(CANDIDATE_3.split())} tokens")
    print(f"\nTest prompts: {len(TEST_PROMPTS)}")
    print(f"Intent options: {INTENT_OPTIONS}")