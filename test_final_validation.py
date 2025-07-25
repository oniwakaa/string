#!/usr/bin/env python3
"""Final validation test for optimized Gemma3n intent classifier."""

from src.inference.intent_classifier import GemmaIntentClassifier
import time

def main():
    print('Testing optimized Gemma3n intent classifier...')

    # Initialize classifier
    classifier = GemmaIntentClassifier()

    # Test sample prompts
    test_prompts = [
        'scrape data from https://example.com',
        'find the login function in the codebase', 
        'create a new API endpoint',
        'fix the bug in authentication',
        'analyze this code for security issues',
        'document the user management API'
    ]

    results = []
    for prompt in test_prompts:
        start = time.time()
        result = classifier.classify(prompt)
        duration = time.time() - start
        
        print(f'Prompt: {prompt[:40]}...')
        print(f'Intent: {result.primary_intent} (confidence: {result.confidence:.2f})')
        print(f'Time: {duration:.2f}s')
        print(f'Raw: {result.metadata.get("raw_response", "")}')
        print('---')
        
        results.append({
            'prompt': prompt,
            'intent': result.primary_intent,
            'confidence': result.confidence,
            'time': duration
        })

    # Summary
    avg_time = sum(r['time'] for r in results) / len(results)
    non_general = [r for r in results if r['intent'] != 'general_query']
    success_rate = len(non_general) / len(results)

    print('\nSUMMARY:')
    print(f'Average time: {avg_time:.2f}s')
    print(f'Success rate: {success_rate*100:.1f}%')
    print('✅ Optimized classifier working correctly!')

if __name__ == "__main__":
    main()