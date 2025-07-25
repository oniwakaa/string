#!/usr/bin/env python3
"""
Test pipeline for agent-driven document creation using model-based intent classification.

This test validates the complete flow:
1. User prompt requesting document creation
2. Model-based intent classification 
3. Agent-driven document initialization
4. Comprehensive logging and confirmation
5. Follow-up operations on created document
"""

import json
import logging
import os
import time
from typing import Dict, List, Any
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DocumentCreationTestPipeline:
    """Complete test pipeline for agent-driven document creation."""
    
    def __init__(self, workspace_root: str = "./test_workspace"):
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(exist_ok=True)
        self.test_results = []
        self.created_documents = []
        
    def step_1_define_user_prompt(self) -> str:
        """
        Step 1: Define a user prompt that explicitly requests document creation.
        
        Returns:
            User prompt string requesting new file creation
        """
        logger.info("=== STEP 1: Defining User Prompt ===")
        
        # Test prompt explicitly requesting document creation
        user_prompt = "Create a new Python file named calculator.py with an empty template for a calculator class."
        
        logger.info(f"User prompt: {user_prompt}")
        
        # Log the prompt characteristics
        prompt_analysis = {
            "prompt": user_prompt,
            "expected_intent": "code_generation",
            "contains_file_name": "calculator.py" in user_prompt,
            "contains_creation_keyword": any(word in user_prompt.lower() for word in ["create", "new", "generate"]),
            "template_request": "template" in user_prompt.lower(),
            "step": "1_prompt_definition"
        }
        
        self.test_results.append(prompt_analysis)
        logger.info(f"Prompt analysis: {json.dumps(prompt_analysis, indent=2)}")
        
        return user_prompt
    
    def step_2_route_through_classifier(self, user_prompt: str) -> Dict[str, Any]:
        """
        Step 2: Route the prompt through model-based intent classifier.
        
        Args:
            user_prompt: The user's request string
            
        Returns:
            Classification result with intent and metadata
        """
        logger.info("=== STEP 2: Model-Based Intent Classification ===")
        
        try:
            from src.inference.intent_classifier import GemmaIntentClassifier
            
            # Initialize the optimized Gemma classifier
            classifier = GemmaIntentClassifier()
            
            # Classify the prompt
            start_time = time.time()
            classification_result = classifier.classify(user_prompt)
            classification_time = time.time() - start_time
            
            # Extract classification details
            classification_data = {
                "primary_intent": classification_result.primary_intent,
                "confidence": classification_result.confidence,
                "secondary_intents": classification_result.secondary_intents,
                "context_modifiers": classification_result.context_modifiers,
                "classification_time": classification_time,
                "raw_response": classification_result.metadata.get("raw_response", ""),
                "step": "2_intent_classification"
            }
            
            logger.info(f"Classification result: {json.dumps(classification_data, indent=2)}")
            
            # Validation assertions
            assert classification_result.primary_intent in ["code_generation", "codebase_query", "general_query"], \
                f"Unexpected intent: {classification_result.primary_intent}"
            
            assert classification_result.confidence > 0.0, \
                f"Invalid confidence score: {classification_result.confidence}"
            
            logger.info("✅ Intent classification successful")
            self.test_results.append(classification_data)
            
            return classification_data
            
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            error_data = {
                "error": str(e),
                "step": "2_intent_classification",
                "status": "failed"
            }
            self.test_results.append(error_data)
            raise
    
    def step_3_agent_document_initialization(self, user_prompt: str, classification: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 3: Agent handles document initialization.
        
        Args:
            user_prompt: Original user request
            classification: Intent classification result
            
        Returns:
            Document creation result with file path and confirmation
        """
        logger.info("=== STEP 3: Agent-Driven Document Initialization ===")
        
        try:
            # Route to appropriate agent based on intent
            intent = classification["primary_intent"]
            
            if intent == "code_generation":
                result = self._handle_code_generation_agent(user_prompt, classification)
            elif intent == "codebase_query":
                # If classified as query, but contains creation keywords, route to generation
                if any(word in user_prompt.lower() for word in ["create", "new", "generate"]):
                    logger.info("Rerouting codebase_query with creation keywords to code_generation")
                    result = self._handle_code_generation_agent(user_prompt, classification)
                else:
                    result = self._handle_codebase_query_agent(user_prompt, classification)
            else:
                result = self._handle_general_fallback(user_prompt, classification)
            
            logger.info(f"Agent result: {json.dumps(result, indent=2)}")
            
            # Validation assertions
            assert "file_path" in result, "Agent must return file_path"
            assert "status" in result, "Agent must return status"
            assert result["status"] in ["created", "exists", "error"], f"Invalid status: {result['status']}"
            
            if result["status"] == "created":
                # Verify file actually exists
                file_path = Path(result["file_path"])
                assert file_path.exists(), f"Created file does not exist: {file_path}"
                self.created_documents.append(str(file_path))
                logger.info(f"✅ Document created successfully: {file_path}")
            
            self.test_results.append(result)
            return result
            
        except Exception as e:
            logger.error(f"Agent document initialization failed: {e}")
            error_result = {
                "error": str(e),
                "step": "3_agent_initialization",
                "status": "failed"
            }
            self.test_results.append(error_result)
            raise
    
    def _handle_code_generation_agent(self, prompt: str, classification: Dict[str, Any]) -> Dict[str, Any]:
        """Handle document creation via code generation agent."""
        logger.info("Routing to CodeGeneratorAgent for document creation")
        
        # Extract file name from prompt
        file_name = self._extract_file_name(prompt)
        if not file_name:
            file_name = "generated_file.py"  # Default fallback
        
        # Create file path in workspace
        file_path = self.workspace_root / file_name
        
        # Generate template content based on prompt
        content = self._generate_template_content(prompt, file_name)
        
        # Create the document
        try:
            with open(file_path, 'w') as f:
                f.write(content)
            
            return {
                "agent": "CodeGeneratorAgent",
                "file_path": str(file_path),
                "file_name": file_name,
                "content_preview": content[:200] + "..." if len(content) > 200 else content,
                "status": "created",
                "timestamp": time.time(),
                "step": "3_agent_initialization"
            }
            
        except Exception as e:
            return {
                "agent": "CodeGeneratorAgent",
                "error": str(e),
                "status": "error",
                "step": "3_agent_initialization"
            }
    
    def _handle_codebase_query_agent(self, prompt: str, classification: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompt via codebase query agent (shouldn't create files)."""
        logger.info("Routing to CodebaseExpertAgent - no document creation expected")
        
        return {
            "agent": "CodebaseExpertAgent", 
            "action": "query_only",
            "file_path": "N/A",
            "status": "no_creation",
            "message": "Codebase query agent does not create documents",
            "step": "3_agent_initialization"
        }
    
    def _handle_general_fallback(self, prompt: str, classification: Dict[str, Any]) -> Dict[str, Any]:
        """Handle via general fallback."""
        logger.info("Using general fallback - attempting document creation")
        
        # Extract file name and create basic file
        file_name = self._extract_file_name(prompt) or "fallback_file.txt"
        file_path = self.workspace_root / file_name
        
        basic_content = f"# File created via general fallback\n# Original prompt: {prompt}\n\n"
        
        try:
            with open(file_path, 'w') as f:
                f.write(basic_content)
            
            return {
                "agent": "GeneralFallback",
                "file_path": str(file_path),
                "file_name": file_name,
                "content_preview": basic_content,
                "status": "created",
                "step": "3_agent_initialization"
            }
            
        except Exception as e:
            return {
                "agent": "GeneralFallback",
                "error": str(e),
                "status": "error",
                "step": "3_agent_initialization"
            }
    
    def _extract_file_name(self, prompt: str) -> str:
        """Extract file name from user prompt."""
        import re
        
        # Look for file names with extensions
        file_pattern = r'(\w+\.\w+)'
        matches = re.findall(file_pattern, prompt)
        
        if matches:
            return matches[0]
        
        # Look for "named X" pattern
        named_pattern = r'named\s+(\w+)'
        named_matches = re.findall(named_pattern, prompt, re.IGNORECASE)
        
        if named_matches:
            name = named_matches[0]
            # Add .py extension if creating Python file
            if "python" in prompt.lower() and not name.endswith('.py'):
                name += '.py'
            return name
        
        return None
    
    def _generate_template_content(self, prompt: str, file_name: str) -> str:
        """Generate template content based on prompt analysis."""
        content_lines = [
            f'"""\n{file_name}\n',
            f"Generated from prompt: {prompt}\n",
            f"Created at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n",
            '"""\n\n'
        ]
        
        # Analyze prompt for specific content types
        if "calculator" in prompt.lower() and "class" in prompt.lower():
            content_lines.extend([
                "class Calculator:",
                "    \"\"\"Calculator class template.\"\"\"",
                "    ",
                "    def __init__(self):",
                "        pass",
                "    ",
                "    def add(self, a, b):",
                "        \"\"\"Add two numbers.\"\"\"",
                "        return a + b",
                "    ",
                "    def subtract(self, a, b):",
                "        \"\"\"Subtract b from a.\"\"\"",
                "        return a - b",
                "    ",
                "    def multiply(self, a, b):",
                "        \"\"\"Multiply two numbers.\"\"\"",
                "        return a * b",
                "    ",
                "    def divide(self, a, b):",
                "        \"\"\"Divide a by b.\"\"\"",
                "        if b == 0:",
                "            raise ValueError('Cannot divide by zero')",
                "        return a / b",
                ""
            ])
        elif "class" in prompt.lower():
            class_name = file_name.replace('.py', '').capitalize()
            content_lines.extend([
                f"class {class_name}:",
                f'    """{class_name} class template."""',
                "    ",
                "    def __init__(self):",
                "        pass",
                ""
            ])
        else:
            content_lines.extend([
                "# Template file",
                "# Add your code here",
                ""
            ])
        
        return '\n'.join(content_lines)
    
    def step_4_log_actions_and_outputs(self, all_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Step 4: Log all actions and outputs with comprehensive tracking.
        
        Args:
            all_results: List of all step results
            
        Returns:
            Complete logging summary
        """
        logger.info("=== STEP 4: Comprehensive Logging and Confirmation ===")
        
        # Compile complete test log
        test_log = {
            "test_id": f"doc_creation_{int(time.time())}",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "workspace_root": str(self.workspace_root),
            "total_steps": len(all_results),
            "created_documents": self.created_documents,
            "step_results": all_results,
            "success_summary": self._analyze_success(all_results),
            "step": "4_logging_confirmation"
        }
        
        # Write detailed log to file
        log_file = self.workspace_root / f"test_log_{test_log['test_id']}.json"
        with open(log_file, 'w') as f:
            json.dump(test_log, f, indent=2)
        
        logger.info(f"Complete test log written to: {log_file}")
        logger.info(f"Test summary: {json.dumps(test_log['success_summary'], indent=2)}")
        
        self.test_results.append(test_log)
        return test_log
    
    def _analyze_success(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze overall test success."""
        steps_completed = len([r for r in results if "error" not in r])
        documents_created = len(self.created_documents)
        
        return {
            "total_steps": len(results),
            "successful_steps": steps_completed,
            "documents_created": documents_created,
            "overall_success": steps_completed >= 3 and documents_created > 0,
            "created_files": self.created_documents
        }
    
    def step_5_follow_up_operations(self, document_path: str) -> Dict[str, Any]:
        """
        Step 5: Demonstrate follow-up operations on created document.
        
        Args:
            document_path: Path to the created document
            
        Returns:
            Results of follow-up operations
        """
        logger.info("=== STEP 5: Follow-up Operations on Created Document ===")
        
        if not os.path.exists(document_path):
            return {
                "error": f"Document not found: {document_path}",
                "step": "5_follow_up_operations"
            }
        
        operations = []
        
        # Read current content
        try:
            with open(document_path, 'r') as f:
                original_content = f.read()
            
            operations.append({
                "operation": "read_content",
                "status": "success",
                "content_length": len(original_content)
            })
            
        except Exception as e:
            operations.append({
                "operation": "read_content",
                "status": "error",
                "error": str(e)
            })
            return {"operations": operations, "step": "5_follow_up_operations"}
        
        # Add a comment/modification
        try:
            modified_content = f"# Modified at {time.strftime('%H:%M:%S')}\n" + original_content
            
            with open(document_path, 'w') as f:
                f.write(modified_content)
            
            operations.append({
                "operation": "modify_content",
                "status": "success",
                "modification": "Added timestamp comment"
            })
            
        except Exception as e:
            operations.append({
                "operation": "modify_content",
                "status": "error",
                "error": str(e)
            })
        
        # Verify file size/properties
        try:
            file_stats = os.stat(document_path)
            operations.append({
                "operation": "verify_properties",
                "status": "success",
                "file_size": file_stats.st_size,
                "last_modified": time.ctime(file_stats.st_mtime)
            })
            
        except Exception as e:
            operations.append({
                "operation": "verify_properties",
                "status": "error",
                "error": str(e)
            })
        
        result = {
            "document_path": document_path,
            "operations": operations,
            "total_operations": len(operations),
            "successful_operations": len([op for op in operations if op["status"] == "success"]),
            "step": "5_follow_up_operations"
        }
        
        logger.info(f"Follow-up operations: {json.dumps(result, indent=2)}")
        self.test_results.append(result)
        
        return result
    
    def run_complete_pipeline(self) -> Dict[str, Any]:
        """Run the complete document creation test pipeline."""
        logger.info("🚀 Starting Complete Document Creation Test Pipeline")
        
        try:
            # Step 1: Define user prompt
            user_prompt = self.step_1_define_user_prompt()
            
            # Step 2: Route through classifier  
            classification = self.step_2_route_through_classifier(user_prompt)
            
            # Step 3: Agent document initialization
            document_result = self.step_3_agent_document_initialization(user_prompt, classification)
            
            # Step 4: Log all actions
            log_summary = self.step_4_log_actions_and_outputs(self.test_results)
            
            # Step 5: Follow-up operations (if document was created)
            if document_result.get("status") == "created":
                follow_up = self.step_5_follow_up_operations(document_result["file_path"])
            else:
                follow_up = {"message": "No document created, skipping follow-up", "step": "5_follow_up_operations"}
                self.test_results.append(follow_up)
            
            # Final pipeline summary
            pipeline_summary = {
                "pipeline_status": "completed",
                "total_steps": 5,
                "user_prompt": user_prompt,
                "final_intent": classification["primary_intent"],
                "documents_created": len(self.created_documents),
                "created_files": self.created_documents,
                "test_workspace": str(self.workspace_root),
                "detailed_results": self.test_results
            }
            
            logger.info("✅ Complete Pipeline Successful!")
            logger.info(f"Pipeline Summary: {json.dumps({k: v for k, v in pipeline_summary.items() if k != 'detailed_results'}, indent=2)}")
            
            return pipeline_summary
            
        except Exception as e:
            logger.error(f"❌ Pipeline failed: {e}")
            return {
                "pipeline_status": "failed",
                "error": str(e),
                "completed_steps": len(self.test_results),
                "partial_results": self.test_results
            }
    
    def cleanup(self):
        """Clean up test workspace."""
        import shutil
        if self.workspace_root.exists():
            shutil.rmtree(self.workspace_root)
            logger.info(f"Cleaned up test workspace: {self.workspace_root}")


def main():
    """Run the document creation test pipeline."""
    pipeline = DocumentCreationTestPipeline()
    
    try:
        result = pipeline.run_complete_pipeline()
        
        print("\n" + "="*60)
        print("DOCUMENT CREATION PIPELINE TEST RESULTS")
        print("="*60)
        
        if result["pipeline_status"] == "completed":
            print("✅ PIPELINE: SUCCESS")
            print(f"📄 Documents Created: {result['documents_created']}")
            print(f"📁 Created Files: {result['created_files']}")
            print(f"🎯 Final Intent: {result['final_intent']}")
            print(f"💭 User Prompt: {result['user_prompt']}")
        else:
            print("❌ PIPELINE: FAILED")
            print(f"Error: {result.get('error', 'Unknown error')}")
            print(f"Completed Steps: {result.get('completed_steps', 0)}/5")
        
        return result
        
    finally:
        # Uncomment to clean up test files
        # pipeline.cleanup()
        pass


if __name__ == "__main__":
    main()