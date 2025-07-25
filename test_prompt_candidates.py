#!/usr/bin/env python3
"""
Test script for minimal prompt candidates with Gemma3n intent classification.
Evaluates prompt effectiveness, stability, and accuracy.
"""

import json
import time
import logging
from typing import Dict, List, Tuple, Any
from prompt_candidates import CURRENT_PROMPT, CANDIDATE_1, CANDIDATE_2, CANDIDATE_3, TEST_PROMPTS, INTENT_OPTIONS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PromptTester:
    """Test different prompt candidates with Gemma3n model."""
    
    def __init__(self):
        self.model = None
        self.results = {}
        
    def _load_model(self):
        """Load Gemma3n model for testing."""
        if self.model is None:
            try:
                import sys
                import os
                src_path = os.path.join(os.path.dirname(__file__), 'src')
                if src_path not in sys.path:
                    sys.path.insert(0, src_path)
                from models.manager import model_manager
                
                logger.info("Loading Gemma3n model for prompt testing...")
                self.model = model_manager.get_model("gemma-3n-E4B-it")
                if not self.model:
                    raise RuntimeError("Failed to load Gemma3n model")
                logger.info("Model loaded successfully")
                
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                raise
    
    def _test_single_prompt(self, template: str, user_prompt: str, intent_list: str) -> Dict[str, Any]:
        """Test a single prompt with the model."""
        try:
            # Format the template
            if "{intents}" in template:
                # For current verbose template - need full intent descriptions
                formatted_prompt = template.format(prompt=user_prompt, intents="- web_research\n- codebase_query\n- code_generation\n- code_editing\n- code_analysis\n- documentation\n- general_query")
            else:
                formatted_prompt = template.format(prompt=user_prompt, intent_list=intent_list)
            
            start_time = time.time()
            
            # Generate response
            response = self.model(
                formatted_prompt,
                max_tokens=50,  # Minimal tokens for simple classification
                temperature=0.1,
                top_p=0.9,
                stop=["User:", "Intent:", "Answer:", "\n\n"]
            )
            
            classification_time = time.time() - start_time
            response_text = response['choices'][0]['text'].strip()
            
            # Parse the response to extract intent
            predicted_intent = self._extract_intent(response_text)
            
            return {
                "success": True,
                "predicted_intent": predicted_intent,
                "raw_response": response_text,
                "classification_time": classification_time,
                "error": None
            }
            
        except Exception as e:
            return {
                "success": False,
                "predicted_intent": "error",
                "raw_response": "",
                "classification_time": 0,
                "error": str(e)
            }
    
    def _extract_intent(self, response: str) -> str:
        """Extract intent from model response."""
        response_lower = response.lower().strip()
        
        # Direct intent matching
        for intent in INTENT_OPTIONS:
            if intent.lower() in response_lower:
                return intent
        
        # Try to find any valid intent name
        for intent in INTENT_OPTIONS:
            if intent.replace("_", " ") in response_lower:
                return intent
                
        # If JSON response, try parsing
        if "{" in response and "}" in response:
            try:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                json_text = response[json_start:json_end]
                data = json.loads(json_text)
                return data.get("primary_intent", "general_query")
            except:
                pass
        
        return "general_query"  # Default fallback
    
    def test_prompt_candidate(self, template: str, candidate_name: str) -> Dict[str, Any]:
        """Test a prompt candidate against all test prompts."""
        logger.info(f"Testing {candidate_name}...")
        
        results = {
            "candidate_name": candidate_name,
            "template": template,
            "total_prompts": len(TEST_PROMPTS),
            "successful_classifications": 0,
            "failed_classifications": 0,
            "average_time": 0,
            "intent_distribution": {},
            "errors": [],
            "details": []
        }
        
        intent_list = ", ".join(INTENT_OPTIONS)
        total_time = 0
        
        for i, test_prompt in enumerate(TEST_PROMPTS):
            logger.info(f"  Testing prompt {i+1}/{len(TEST_PROMPTS)}: {test_prompt[:50]}...")
            
            result = self._test_single_prompt(template, test_prompt, intent_list)
            results["details"].append({
                "input_prompt": test_prompt,
                "result": result
            })
            
            if result["success"]:
                results["successful_classifications"] += 1
                intent = result["predicted_intent"]
                results["intent_distribution"][intent] = results["intent_distribution"].get(intent, 0) + 1
                total_time += result["classification_time"]
            else:
                results["failed_classifications"] += 1
                results["errors"].append(result["error"])
        
        if results["successful_classifications"] > 0:
            results["average_time"] = total_time / results["successful_classifications"]
        
        return results
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run tests for all prompt candidates."""
        self._load_model()
        
        candidates = [
            (CURRENT_PROMPT, "Current Verbose"),
            (CANDIDATE_1, "Ultra-minimal"),
            (CANDIDATE_2, "Simple Structured"),
            (CANDIDATE_3, "Direct Command")
        ]
        
        all_results = {}
        
        for template, name in candidates:
            try:
                result = self.test_prompt_candidate(template, name)
                all_results[name] = result
                
                logger.info(f"{name} Results:")
                logger.info(f"  Success rate: {result['successful_classifications']}/{result['total_prompts']} ({result['successful_classifications']/result['total_prompts']*100:.1f}%)")
                logger.info(f"  Average time: {result['average_time']:.2f}s")
                logger.info(f"  Intent distribution: {result['intent_distribution']}")
                
            except Exception as e:
                logger.error(f"Failed to test {name}: {e}")
                all_results[name] = {"error": str(e)}
        
        return all_results
    
    def save_results(self, results: Dict[str, Any], filename: str = "prompt_test_results.json"):
        """Save test results to file."""
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {filename}")

if __name__ == "__main__":
    tester = PromptTester()
    results = tester.run_all_tests()
    tester.save_results(results)
    
    # Print summary
    print("\n=== PROMPT TEST SUMMARY ===")
    for candidate_name, result in results.items():
        if "error" in result:
            print(f"{candidate_name}: ERROR - {result['error']}")
        else:
            success_rate = result['successful_classifications'] / result['total_prompts'] * 100
            print(f"{candidate_name}: {success_rate:.1f}% success, {result['average_time']:.2f}s avg")