"""
CodeEditorAgent - Precise code modification specialist.

This agent takes a block of code and a list of specific instructions and produces
a new version of the code with only the requested changes applied. It is designed
for precision, not creativity.
"""

import ast
import re
import sys
import os
from typing import Any, Dict, Optional

from agents.base import BaseAgent, Task, Result

# Add src to path for ModelManager import
src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)
from models.manager import model_manager


class CodeEditorAgent(BaseAgent):
    """
    An agent specialized in making precise edits to existing code
    based on a structured set of instructions.
    
    This agent is designed to be:
    - Precise: Only makes the requested changes
    - Conservative: Preserves all existing functionality 
    - Accurate: Validates syntax and structure
    - Predictable: No creative interpretations
    """

    def __init__(self):
        """Initialize the CodeEditorAgent with SmolLM3-3B model."""
        super().__init__(
            name="SmolLM_CodeEditor",
            role="code_editor",
            model_name="SmolLM3-3B"
        )
        
        # Configuration for precise editing using llama-cpp-python
        self.llama_config = {
            'n_ctx': 4096,  # Context length
            'n_batch': 512,
            'n_gpu_layers': -1,  # Use all available GPU layers
            'use_mmap': True,
            'use_mlock': False,
            'low_vram': True,
            'verbose': False
        }
        
        # Generation settings for precision
        self.generation_config = {
            'max_tokens': 2048,
            'temperature': 0.1,  # Very low temperature for precision
            'top_p': 0.8,
            'top_k': 20,
            'repeat_penalty': 1.1,
            'stop': ["```", "---", "EXPLANATION:", "Note:", "\n\n\n"],
        }

    async def execute(self, task: Task) -> Result:
        """
        Executes the code editing task with precision and validation.
        
        Args:
            task: Task object containing:
                - prompt: Specific editing instructions
                - context: Must contain 'code_to_edit' and optionally 'language'
                
        Returns:
            Result: Contains the precisely edited code or error information
        """
        try:
            # Ensure model is loaded
            if self.model is None:
                self.lazy_load_model()

            # Validate required inputs
            original_code = task.context.get("code_to_edit")
            instructions = task.prompt

            if not original_code:
                return Result(
                    task_id=task.task_id,
                    status="failure",
                    output="",
                    error_message="Missing required 'code_to_edit' in task context"
                )

            if not instructions:
                return Result(
                    task_id=task.task_id,
                    status="failure",
                    output="",
                    error_message="Missing editing instructions in task prompt"
                )

            # Set processing status
            self.status = 'processing'

            # Step 1: Construct the precision-focused prompt
            prompt = self._construct_prompt(task)

            # Step 2: Generate response with the model
            raw_response = self._generate_with_llama(prompt)

            # Step 3: Parse and validate the output
            language = task.context.get("language", "python")
            edited_code = self._parse_and_validate_output(raw_response, language)

            # Reset status
            self.status = 'ready'

            # Suggest next action - save the edited code
            metadata = self._analyze_for_next_action(task, edited_code)

            return Result(
                task_id=task.task_id,
                status="success",
                output=edited_code,
                metadata=metadata
            )

        except Exception as e:
            self.status = 'error'
            error_msg = f"CodeEditorAgent failed: {str(e)}"
            print(f"❌ {error_msg}")
            
            return Result(
                task_id=task.task_id,
                status="failure",
                output="",
                error_message=error_msg
            )

    def _construct_prompt(self, task: Task) -> str:
        """
        Constructs a highly constrained prompt for the LLM to ensure precision.
        
        The prompt is designed to:
        - Clearly separate original code from instructions
        - Constrain the model to make only requested changes
        - Prevent explanations or creative additions
        - Ensure clean code-only output
        """
        original_code = task.context.get("code_to_edit")
        instructions = task.prompt
        language = task.context.get("language", "python")

        if not original_code or not instructions:
            raise ValueError("Task is missing required 'code_to_edit' in context or instructions in prompt.")

        # Multi-part prompt designed for maximum precision
        prompt_parts = [
            "You are an expert code editor. Your task is to apply specific changes to a block of code.",
            "You must not alter any other part of the code beyond what is explicitly requested.",
            "Do not add comments, explanations, or any text outside the code block.",
            "",
            "--- ORIGINAL CODE ---",
            original_code,
            "--- END ORIGINAL CODE ---",
            "",
            f"Language: {language}",
            "",
            "Apply the following instructions exactly as described:",
            instructions,
            "",
            "IMPORTANT RULES:",
            "1. Make ONLY the changes specified in the instructions",
            "2. Preserve all existing functionality not mentioned in instructions", 
            "3. Maintain the original code structure and style",
            "4. Ensure proper syntax and indentation",
            "5. Do not add explanatory comments unless specifically requested",
            "",
            "Your response MUST contain ONLY the complete, fully modified code block.",
            "Do not include explanations, markdown formatting, or any surrounding text.",
            "",
            "Modified code:"
        ]
        
        return "\n".join(prompt_parts)

    def _parse_and_validate_output(self, llm_response: str, language: str) -> str:
        """
        Parses the LLM's response to extract and validate the code.
        
        This method:
        - Extracts code from various response formats
        - Validates syntax for supported languages
        - Cleans up formatting issues
        - Ensures the code is ready for use
        """
        # Step 1: Extract the code from the response
        extracted_code = self._extract_code_block(llm_response)
        
        if not extracted_code:
            raise ValueError("LLM response did not contain a valid code block")

        # Step 2: Clean up the extracted code
        cleaned_code = self._clean_code_output(extracted_code)

        # Step 3: Validate syntax for supported languages
        self._validate_syntax(cleaned_code, language)

        return cleaned_code

    def _extract_code_block(self, response: str) -> str:
        """Extract code from various response formats."""
        response = response.strip()
        
        # Try to extract from markdown code blocks first
        code_block_pattern = r'```(?:\w+)?\s*(.*?)\s*```'
        matches = re.findall(code_block_pattern, response, re.DOTALL)
        
        if matches:
            # Take the first (and presumably only) code block
            return matches[0].strip()
        
        # Try to extract from simple backticks
        simple_code_pattern = r'`([^`]+)`'
        matches = re.findall(simple_code_pattern, response)
        
        if matches and len(matches) == 1:
            return matches[0].strip()
        
        # If no code blocks found, check if the entire response looks like code
        if self._looks_like_code(response):
            return response
        
        # Try to find code after "Modified code:" or similar markers
        code_markers = [
            "Modified code:",
            "Updated code:",
            "Edited code:",
            "Result:",
            "Output:"
        ]
        
        for marker in code_markers:
            if marker in response:
                code_part = response.split(marker, 1)[1].strip()
                if code_part:
                    return code_part
        
        # Last resort: return the whole response if it's not empty
        if response:
            return response
        
        return ""

    def _clean_code_output(self, code: str) -> str:
        """Clean up common formatting issues in generated code."""
        # Remove leading/trailing whitespace
        code = code.strip()
        
        # Remove any remaining markdown artifacts
        code = re.sub(r'^```\w*\s*', '', code)
        code = re.sub(r'\s*```$', '', code)
        
        # Remove explanatory text that might have leaked through
        lines = code.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Skip lines that look like explanations
            if any(phrase in line.lower() for phrase in [
                'here is', 'here\'s', 'the modified', 'the updated', 
                'i have', 'i\'ve', 'explanation:', 'note:'
            ]):
                continue
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)

    def _looks_like_code(self, text: str) -> bool:
        """Heuristic to determine if text looks like code."""
        # Check for common code indicators
        code_indicators = [
            'def ', 'class ', 'import ', 'from ', 'if ', 'for ', 'while ',
            'function ', 'var ', 'let ', 'const ', 'public ', 'private ',
            '{', '}', '()', '[]', ';', '//', '/*', '*/', '#'
        ]
        
        # Count how many lines look like code
        lines = text.split('\n')
        code_like_lines = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if line contains code indicators
            if any(indicator in line for indicator in code_indicators):
                code_like_lines += 1
            # Check for indentation patterns
            elif line.startswith('    ') or line.startswith('\t'):
                code_like_lines += 1
        
        # If more than 50% of non-empty lines look like code, consider it code
        non_empty_lines = len([l for l in lines if l.strip()])
        return non_empty_lines > 0 and (code_like_lines / non_empty_lines) > 0.5

    def _validate_syntax(self, code: str, language: str) -> None:
        """Validate the syntax of the generated code."""
        language = language.lower()
        
        if language == "python":
            try:
                ast.parse(code)
            except SyntaxError as e:
                raise ValueError(f"Generated Python code has syntax error: {e}")
        
        elif language in ["javascript", "js"]:
            # Basic JavaScript validation (check for balanced braces/brackets)
            if not self._check_balanced_delimiters(code):
                raise ValueError("Generated JavaScript code has unbalanced delimiters")
        
        elif language in ["java", "c", "cpp", "c++"]:
            # Basic validation for C-style languages
            if not self._check_balanced_delimiters(code):
                raise ValueError(f"Generated {language} code has unbalanced delimiters")
        
        # For other languages, we skip syntax validation
        # but still check for basic structural issues
        elif not code.strip():
            raise ValueError("Generated code is empty")

    def _check_balanced_delimiters(self, code: str) -> bool:
        """Check if code has balanced braces, brackets, and parentheses."""
        stack = []
        pairs = {'(': ')', '[': ']', '{': '}'}
        
        for char in code:
            if char in pairs:
                stack.append(char)
            elif char in pairs.values():
                if not stack:
                    return False
                if pairs[stack.pop()] != char:
                    return False
        
        return len(stack) == 0

    def lazy_load_model(self):
        """Load the SmolLM model using llama-cpp-python."""
        if self.model is None:
            try:
                from llama_cpp import Llama
                import os
                
                self.status = 'loading_model'
                print(f"🔄 Loading SmolLM model for {self.name}...")
                
                # Use ModelManager to get shared model instance (no direct loading)
                self.model = model_manager.get_model(self.model_name)
                if not self.model:
                    raise RuntimeError(f"ModelManager failed to load model: {self.model_name}")
                
                self.status = 'ready'
                print(f"✅ SmolLM model loaded successfully for {self.name}")
                
            except Exception as e:
                self.status = 'error'
                error_msg = f"Failed to load SmolLM model for {self.name}: {str(e)}"
                print(f"❌ {error_msg}")
                raise RuntimeError(error_msg)

    def _generate_with_llama(self, prompt: str) -> str:
        """Generate response using llama-cpp-python."""
        if self.model is None:
            raise RuntimeError(f"Model not loaded for {self.name}")
        
        try:
            response = self.model(
                prompt,
                max_tokens=self.generation_config['max_tokens'],
                temperature=self.generation_config['temperature'],
                top_p=self.generation_config['top_p'],
                top_k=self.generation_config['top_k'],
                repeat_penalty=self.generation_config['repeat_penalty'],
                stop=self.generation_config['stop'],
                echo=False
            )
            
            return response['choices'][0]['text'].strip()
            
        except Exception as e:
            raise RuntimeError(f"Generation failed for {self.name}: {str(e)}")

    def get_supported_languages(self) -> list[str]:
        """Return list of languages with syntax validation support."""
        return ["python", "javascript", "js", "java", "c", "cpp", "c++"]

    def _analyze_for_next_action(self, task: Task, edited_code: str) -> dict:
        """
        Analyze the editing task to suggest next actions.
        
        Args:
            task: The original task with context
            edited_code: The edited code result
            
        Returns:
            Metadata dictionary with next_action suggestions
        """
        metadata = {}
        
        # Get original file path from context if available
        original_context = task.context
        file_path = None
        
        # Look for file path hints in context
        for key, value in original_context.items():
            if 'path' in key.lower() and isinstance(value, str):
                file_path = value
                break
            elif 'file' in key.lower() and isinstance(value, str) and '.' in value:
                file_path = value
                break
        
        # If no file path found, try to extract from prompt
        if not file_path:
            prompt_lower = task.prompt.lower()
            if 'file' in prompt_lower:
                import re
                # Look for file references in the prompt
                file_patterns = [
                    r'file\s+["\']([^"\']+\.[a-zA-Z]+)["\']',
                    r'in\s+["\']([^"\']+\.[a-zA-Z]+)["\']',
                    r'["\']([^"\']+\.py)["\']'
                ]
                
                for pattern in file_patterns:
                    match = re.search(pattern, task.prompt)
                    if match:
                        file_path = match.group(1)
                        break
        
        # If still no path, generate one based on the code content
        if not file_path:
            import re
            if 'class ' in edited_code:
                class_match = re.search(r'class\s+(\w+)', edited_code)
                if class_match:
                    class_name = class_match.group(1)
                    file_path = f"{class_name.lower()}_edited.py"
                else:
                    file_path = "edited_class.py"
            elif 'def ' in edited_code:
                func_match = re.search(r'def\s+(\w+)', edited_code)
                if func_match:
                    func_name = func_match.group(1)
                    file_path = f"{func_name}_edited.py"
                else:
                    file_path = "edited_functions.py"
            else:
                file_path = "edited_code.py"
        
        # Suggest saving the edited code
        metadata['next_action'] = {
            'tool': 'edit_file',
            'args': {
                'file_path': file_path,
                'content': edited_code,
                'create_backup': True
            }
        }
        
        print(f"💡 Suggesting file edit: {file_path}")
        return metadata